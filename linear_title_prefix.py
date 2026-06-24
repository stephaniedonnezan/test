"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "
STATUS_FIELD_NAMES = frozenset({"status", "state", "workflowstate", "workflow status"})
STATUS_TRIGGER_NAMES = frozenset(
    {
        "statuschanged",
        "statuschange",
        "statusupdated",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }
)
GENERIC_UPDATE_NAMES = frozenset(
    {
        "update",
        "updated",
        "issueupdate",
        "issueupdated",
        "updatedissue",
    }
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for status changes to To Research.

    The function is intentionally side-effect free so automation runtimes can
    decide how to apply the returned action to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _payload_candidates(event)
    if not _is_status_change_event(event, payloads):
        return None

    new_status = _extract_new_status(payloads)
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _extract_issue_id(payloads)
    title = _extract_title(payloads)
    if not issue_id or not title:
        return None

    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}{TITLE_SEPARATOR}{title}",
    }


def _payload_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = [event]
    _append_mapping(candidates, event.get("automation_trigger_info"))
    _append_mapping(candidates, event.get("triggerContext"))
    _append_mapping(candidates, event.get("data"))
    _append_mapping(candidates, event.get("issue"))
    _append_mapping(candidates, event.get("node"))

    for container_key in ("automation_trigger_info", "triggerContext", "data"):
        container = event.get(container_key)
        if isinstance(container, Mapping):
            _append_mapping(candidates, container.get("triggerContext"))
            _append_mapping(candidates, container.get("issue"))
            _append_mapping(candidates, container.get("node"))

    return candidates


def _append_mapping(candidates: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping) and value not in candidates:
        candidates.append(value)


def _is_status_change_event(
    event: Mapping[str, Any], payloads: Sequence[Mapping[str, Any]]
) -> bool:
    event_names = _event_names(payloads)
    if any(name in STATUS_TRIGGER_NAMES for name in event_names):
        return True

    if any(name in GENERIC_UPDATE_NAMES for name in event_names):
        return _updated_fields_include_status(event, payloads)

    # Cursor automations can provide only newStatus/status in triggerContext.
    return _has_key_anywhere(payloads, ("newStatus", "new_status", "statusName", "status_name"))


def _event_names(payloads: Sequence[Mapping[str, Any]]) -> list[str]:
    names: list[str] = []
    for payload in payloads:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            value = payload.get(key)
            if isinstance(value, str):
                names.append(_normalize_token(value))
    return names


def _updated_fields_include_status(
    event: Mapping[str, Any], payloads: Sequence[Mapping[str, Any]]
) -> bool:
    for payload in payloads:
        updated_fields = payload.get("updatedFields")
        if _field_list_has_status(updated_fields):
            return True

        changed_fields = payload.get("changedFields")
        if _field_list_has_status(changed_fields):
            return True

        changes = payload.get("changes")
        if _changes_include_status(changes):
            return True

    previous = event.get("previous") or event.get("before")
    current = event.get("current") or event.get("after")
    if isinstance(previous, Mapping) and isinstance(current, Mapping):
        return any(
            previous.get(field) != current.get(field)
            for field in ("status", "state", "workflowState")
        )

    return False


def _field_list_has_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELD_NAMES

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_field_list_has_status(item) for item in value)

    if isinstance(value, Mapping):
        return any(_normalize_field_name(str(key)) in STATUS_FIELD_NAMES for key in value)

    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _normalize_field_name(str(key)) in STATUS_FIELD_NAMES:
                return True
            if isinstance(change, Mapping) and _changes_include_status(change):
                return True
        return False

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for change in value:
            if isinstance(change, Mapping):
                field = change.get("field") or change.get("name") or change.get("key")
                if isinstance(field, str) and _normalize_field_name(field) in STATUS_FIELD_NAMES:
                    return True
                if _changes_include_status(change):
                    return True
        return False

    return False


def _extract_new_status(payloads: Sequence[Mapping[str, Any]]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _first_string_value(payloads, key)
        if value:
            return value

    for payload in payloads:
        changes = payload.get("changes")
        status_name = _status_from_changes(changes)
        if status_name:
            return status_name

    for payload in payloads:
        for key in ("state", "workflowState", "status"):
            value = payload.get(key)
            status_name = _name_from_value(value)
            if status_name:
                return status_name

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, change in changes.items():
            if _normalize_field_name(str(key)) in STATUS_FIELD_NAMES:
                status_name = _name_from_change(change)
                if status_name:
                    return status_name
            if isinstance(change, Mapping):
                nested = _status_from_changes(change)
                if nested:
                    return nested

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("name") or change.get("key")
            if isinstance(field, str) and _normalize_field_name(field) in STATUS_FIELD_NAMES:
                status_name = _name_from_change(change)
                if status_name:
                    return status_name
            nested = _status_from_changes(change)
            if nested:
                return nested

    return None


def _name_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "current", "value"):
            status_name = _name_from_value(change.get(key))
            if status_name:
                return status_name
    return _name_from_value(change)


def _extract_issue_id(payloads: Sequence[Mapping[str, Any]]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = _first_string_value(payloads, key)
        if value:
            return value
    return None


def _extract_title(payloads: Sequence[Mapping[str, Any]]) -> str | None:
    for key in ("title", "name"):
        value = _first_string_value(payloads, key)
        if value:
            return value
    return None


def _first_string_value(payloads: Sequence[Mapping[str, Any]], key: str) -> str | None:
    for payload in payloads:
        value = payload.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _name_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested_value = value.get(key)
            if isinstance(nested_value, str) and nested_value.strip():
                return nested_value.strip()

    return None


def _has_title_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _has_key_anywhere(payloads: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> bool:
    return any(any(key in payload for key in keys) for payload in payloads)


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(_split_words(value))


def _normalize_token(value: str) -> str:
    return "".join(_split_words(value))


def _normalize_field_name(value: str) -> str:
    return " ".join(_split_words(value))


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    return [part.casefold() for part in re.split(r"[^A-Za-z0-9]+", spaced) if part]


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is None:
        return 0

    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
