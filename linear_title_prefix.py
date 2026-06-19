"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = frozenset(
    {
        "status",
        "state",
        "workflowstate",
        "workflowstatus",
    }
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payloads = _candidate_payloads(event)
    if not _is_status_change_event(payloads):
        return None

    status = _first_text(_status_candidates(payloads))
    if _normalize_status(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(_field_candidates(payloads, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _first_text(_field_candidates(payloads, ("title", "name")))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return nested payloads from most specific trigger data to broader data."""
    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is payload for payload in payloads):
            payloads.append(value)

    trigger_context = event.get("triggerContext")
    automation_trigger_info = event.get("automation_trigger_info")
    if isinstance(automation_trigger_info, Mapping):
        add(automation_trigger_info.get("triggerContext"))

    add(trigger_context)
    add(event)

    for payload in list(payloads):
        data = payload.get("data")
        issue = payload.get("issue")

        if isinstance(data, Mapping):
            add(data.get("issue"))
            add(data)
        if isinstance(issue, Mapping):
            add(issue)

    return payloads


def _is_status_change_event(payloads: Iterable[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        event_tokens = _normalized_tokens(
            _field_candidates(payloads=(payload,), keys=("trigger", "webhookType", "action", "type", "event"))
        )
        if any(token in {"statuschanged", "statechanged", "workflowstatechanged"} for token in event_tokens):
            return True

        changed_fields = _changed_fields(payload)
        if changed_fields & STATUS_FIELDS:
            return True

    return False


def _status_candidates(payloads: Iterable[Mapping[str, Any]]) -> Iterable[Any]:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for payload in payloads:
        yield from _field_candidates((payload,), explicit_keys)
        yield from _change_status_candidates(payload)

    for payload in payloads:
        yield from _field_candidates((payload,), fallback_keys)


def _change_status_candidates(payload: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("changes", "updatedFrom"):
        changes = payload.get(key)
        if not isinstance(changes, Mapping):
            continue

        for field, value in changes.items():
            if _normalize_key(field) not in STATUS_FIELDS:
                continue
            if isinstance(value, Mapping):
                for candidate_key in ("to", "new", "after", "name"):
                    yield value.get(candidate_key)
            else:
                yield value


def _field_candidates(payloads: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Iterable[Any]:
    normalized_keys = [_normalize_key(key) for key in keys]
    for payload in payloads:
        normalized_items = [(_normalize_key(key), value) for key, value in payload.items()]
        for wanted_key in normalized_keys:
            for normalized_key, value in normalized_items:
                if normalized_key != wanted_key:
                    continue
                if isinstance(value, Mapping):
                    yield from _field_candidates((value,), ("name", "title", "id"))
                else:
                    yield value


def _changed_fields(payload: Mapping[str, Any]) -> set[str]:
    fields: set[str] = set()

    for key in ("updatedFields", "changedFields"):
        raw_fields = payload.get(key)
        if isinstance(raw_fields, str):
            fields.add(_normalize_key(raw_fields))
        elif isinstance(raw_fields, Iterable) and not isinstance(raw_fields, (bytes, bytearray, Mapping)):
            fields.update(_normalize_key(field) for field in raw_fields)

    for key in ("changes", "updatedFrom"):
        changes = payload.get(key)
        if isinstance(changes, Mapping):
            fields.update(_normalize_key(field) for field in changes)

    return fields


def _first_text(values: Iterable[Any]) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalized_tokens(values: Iterable[Any]) -> set[str]:
    return {_normalize_key(value) for value in values if value is not None}


def _normalize_status(value: str | None) -> str:
    if value is None:
        return ""
    return _split_camel_case(str(value)).replace("_", " ").replace("-", " ").strip().lower()


def _normalize_key(value: Any) -> str:
    text = _split_camel_case(str(value))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    """Read a JSON event from stdin and print an update action if one applies."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
