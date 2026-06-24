"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "stateid",
    "workflowstateid",
}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    payloads = _candidate_payloads(event)
    if not _is_status_change_event(payloads):
        return None

    status = _first_text(_status_candidates(payloads))
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(_field_candidates(payloads, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _first_text(_field_candidates(payloads, ("title", "name")))
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


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely metadata and issue objects from Cursor and Linear payloads."""

    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            payloads.append(value)

    add(event)
    add(event.get("triggerContext"))

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        add(automation_info)
        add(automation_info.get("triggerContext"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data)
        add(data.get("issue"))

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        add(issue)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        data = trigger_context.get("data")
        if isinstance(data, Mapping):
            add(data)
            add(data.get("issue"))

    return payloads


def _is_status_change_event(payloads: Sequence[Mapping[str, Any]]) -> bool:
    event_names = [
        _normalize_event_name(value)
        for payload in payloads
        for value in _field_candidates(payloads=(payload,), field_names=("trigger", "action", "type", "webhookType"))
    ]

    if any(name == "statuschanged" for name in event_names):
        return True

    if any(name in {"issueupdated", "updatedissue", "update"} for name in event_names):
        return _mentions_status_change(payloads)

    return False


def _mentions_status_change(payloads: Sequence[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        for key in ("updatedFields", "changedFields"):
            if _sequence_mentions_status(payload.get(key)):
                return True

        for key in ("changes", "updatedFrom"):
            value = payload.get(key)
            if isinstance(value, Mapping) and any(_is_status_field(name) for name in value):
                return True

    return False


def _sequence_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_is_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_event_name(value) in STATUS_FIELD_NAMES


def _status_candidates(payloads: Sequence[Mapping[str, Any]]) -> list[Any]:
    candidates: list[Any] = []

    for payload in payloads:
        candidates.extend(
            _field_candidates(
                payloads=(payload,),
                field_names=(
                    "newStatus",
                    "new_status",
                    "statusName",
                    "stateName",
                    "workflowStateName",
                ),
            )
        )
        candidates.extend(_changed_status_candidates(payload))

    for payload in payloads:
        candidates.extend(_field_candidates(payloads=(payload,), field_names=("status",)))
        candidates.extend(_name_from_mapping(payload.get("state")))
        candidates.extend(_name_from_mapping(payload.get("workflowState")))
        candidates.extend(_field_candidates(payloads=(payload,), field_names=("state", "workflowState")))

    return candidates


def _changed_status_candidates(payload: Mapping[str, Any]) -> list[Any]:
    candidates: list[Any] = []
    for container_name in ("changes", "updatedFrom"):
        container = payload.get(container_name)
        if not isinstance(container, Mapping):
            continue

        for field_name, change in container.items():
            if not _is_status_field(field_name):
                continue

            if isinstance(change, Mapping):
                for key in ("to", "new", "newValue", "value"):
                    value = change.get(key)
                    candidates.extend(_name_from_mapping(value))
                    candidates.append(value)
            else:
                candidates.append(change)

    return candidates


def _field_candidates(
    payloads: Sequence[Mapping[str, Any]], field_names: Sequence[str]
) -> list[Any]:
    values: list[Any] = []
    for payload in payloads:
        for field_name in field_names:
            if field_name in payload:
                values.append(payload[field_name])
    return values


def _name_from_mapping(value: Any) -> list[Any]:
    if isinstance(value, Mapping):
        return _field_candidates(payloads=(value,), field_names=("name", "title", "label"))
    return []


def _first_text(values: Sequence[Any]) -> str | None:
    for value in values:
        if isinstance(value, Mapping):
            nested = _first_text(_name_from_mapping(value))
            if nested:
                return nested
            continue
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(value))
    words = re.sub(r"[^a-zA-Z0-9]+", " ", words)
    return " ".join(words.lower().split())


def _normalize_event_name(value: Any) -> str:
    text = _normalize_text(None if value is None else str(value)) or ""
    return text.replace(" ", "")


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
