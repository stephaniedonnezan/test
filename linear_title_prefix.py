"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = frozenset(
    {
        "status",
        "state",
        "workflowstate",
        "workflow_state",
        "workflowStatus",
        "workflow_status",
    }
)


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters To Research."""
    if not isinstance(event, Mapping):
        return None

    payloads = _payload_candidates(event)
    if not _is_status_change_event(payloads):
        return None

    new_status = _first_text(_status_candidates(payloads))
    if _normalize_status(new_status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _first_text(_value_candidates(payloads, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _first_text(_value_candidates(payloads, ("title", "name")))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _payload_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(event)
    for key in ("triggerContext", "webhook", "payload"):
        add(event.get(key))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))

    issue = event.get("issue")
    add(issue)
    return candidates


def _is_status_change_event(payloads: Sequence[Mapping[str, Any]]) -> bool:
    event_texts = _value_candidates(payloads, ("trigger", "triggerType", "webhookType", "action", "type"))
    if any(_looks_like_status_change(text) for text in event_texts):
        return True

    if any(_looks_like_issue_update(text) for text in event_texts):
        return any(_contains_status_field(payload.get("updatedFields")) for payload in payloads) or any(
            _contains_status_field(payload.get("changedFields")) for payload in payloads
        ) or any(_changes_include_status(payload.get("changes")) for payload in payloads)

    return any(_contains_status_field(payload.get("updatedFields")) for payload in payloads) or any(
        _changes_include_status(payload.get("changes")) for payload in payloads
    )


def _looks_like_status_change(value: Any) -> bool:
    normalized = _normalize_key(value)
    return normalized in {
        "statuschanged",
        "statuschange",
        "statuschangedissue",
        "statechanged",
        "workflowstatechanged",
    }


def _looks_like_issue_update(value: Any) -> bool:
    normalized = _normalize_key(value)
    return normalized in {"update", "updated", "issueupdated", "updatedissue"}


def _status_candidates(payloads: Sequence[Mapping[str, Any]]) -> list[Any]:
    values: list[Any] = []
    values.extend(_value_candidates(payloads, ("newStatus", "new_status", "toStatus", "to_status")))
    values.extend(_change_new_values(payloads))

    for payload in payloads:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = payload.get(key)
            if isinstance(value, Mapping):
                values.extend(_nested_name_values(value))
            else:
                values.append(value)

    return values


def _value_candidates(payloads: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> list[Any]:
    values: list[Any] = []
    for payload in payloads:
        for key in keys:
            if key in payload:
                values.append(payload[key])
    return values


def _nested_name_values(value: Mapping[str, Any]) -> list[Any]:
    return [value.get(key) for key in ("name", "title", "label", "status")]


def _change_new_values(payloads: Sequence[Mapping[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for payload in payloads:
        changes = payload.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, change in changes.items():
            if _normalize_key(key) not in {_normalize_key(field) for field in STATUS_FIELDS}:
                continue

            if isinstance(change, Mapping):
                for new_key in ("new", "to", "after", "newValue", "new_value"):
                    new_value = change.get(new_key)
                    if isinstance(new_value, Mapping):
                        values.extend(_nested_name_values(new_value))
                    else:
                        values.append(new_value)
            else:
                values.append(change)

    return values


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in {_normalize_key(field) for field in STATUS_FIELDS}

    if isinstance(value, Mapping):
        return any(_contains_status_field(key) or _contains_status_field(item) for key, item in value.items())

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _changes_include_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(_normalize_key(key) in {_normalize_key(field) for field in STATUS_FIELDS} for key in value)


def _first_text(values: Sequence[Any]) -> str | None:
    for value in values:
        text = _coerce_text(value)
        if text:
            return text
    return None


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return _first_text(_nested_name_values(value))
    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor\s+researching\b", title, flags=re.IGNORECASE) is not None


def _normalize_status(value: Any) -> str | None:
    text = _coerce_text(value)
    if not text:
        return None

    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _normalize_key(value: Any) -> str:
    text = _coerce_text(value) or ""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
