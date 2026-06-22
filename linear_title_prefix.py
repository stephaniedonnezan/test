"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "workflow state changed",
}
_UPDATE_TRIGGERS = {
    "issue update",
    "issue updated",
    "update",
    "updated",
    "updated issue",
}
_STATUS_FIELDS = {"status", "state", "workflow state", "workflowstate"}
_EXPLICIT_NEW_STATUS_KEYS = {
    "new status",
    "newstatus",
    "to status",
    "tostatus",
    "target status",
    "targetstatus",
    "status name",
    "statusname",
    "state name",
    "statename",
    "workflow state name",
    "workflowstatename",
}
_STATUS_FALLBACK_KEYS = {"status", "state", "workflow state", "workflowstate"}
_STATUS_CHANGE_CONTAINER_KEYS = {
    "changes",
    "change",
    "updated fields",
    "updatedfields",
    "changed fields",
    "changedfields",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    title = _first_string_for_keys(event, ("title",))
    if title is None:
        return None

    title = title.strip()
    if not title or title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    issue_id = _first_string_for_keys(
        event,
        ("issueId", "issue_id", "identifier", "key", "id"),
    )
    if issue_id is None:
        return None

    issue_id = issue_id.strip()
    if not issue_id:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_types = {
        _normalize_text(value)
        for value in _values_for_keys(event, ("trigger", "webhookType", "action", "type"))
    }

    if event_types & _STATUS_CHANGE_TRIGGERS:
        return True

    return bool(event_types & _UPDATE_TRIGGERS) and _event_mentions_status_field(event)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for value in _values_for_normalized_keys(event, _EXPLICIT_NEW_STATUS_KEYS):
        status = _status_value(value)
        if status:
            return status

    changed_status = _status_from_change_containers(event)
    if changed_status:
        return changed_status

    for value in _values_for_normalized_keys(event, _STATUS_FALLBACK_KEYS):
        status = _status_value(value)
        if status:
            return status

    return None


def _status_from_change_containers(event: Mapping[str, Any]) -> str | None:
    for container in _values_for_normalized_keys(event, _STATUS_CHANGE_CONTAINER_KEYS):
        status = _status_from_change_container(container)
        if status:
            return status
    return None


def _status_from_change_container(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, field_value in value.items():
            if _normalize_field_name(key) in _STATUS_FIELDS:
                status = _status_value(field_value)
                if status:
                    return status
        for key in ("to", "new", "after", "newValue", "new_value"):
            if key in value:
                status = _status_value(value[key])
                if status:
                    return status
        for nested in value.values():
            status = _status_from_change_container(nested)
            if status:
                return status
    elif _is_sequence(value):
        for item in value:
            status = _status_from_change_container(item)
            if status:
                return status
    return None


def _event_mentions_status_field(event: Mapping[str, Any]) -> bool:
    for value in _values_for_normalized_keys(event, _STATUS_CHANGE_CONTAINER_KEYS):
        if _contains_status_field(value):
            return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELDS

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _normalize_field_name(key) in _STATUS_FIELDS:
                return True
            if _normalize_field_name(key) in {"field", "field name", "fieldname", "name"}:
                if _contains_status_field(nested):
                    return True
            if _contains_status_field(nested):
                return True
        return False

    if _is_sequence(value):
        return any(_contains_status_field(item) for item in value)

    return False


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in (
            "to",
            "new",
            "after",
            "newValue",
            "new_value",
            "name",
            "title",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ):
            if key in value:
                status = _status_value(value[key])
                if status:
                    return status

    return None


def _first_string_for_keys(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        normalized_key = _normalize_field_name(key)
        for mapping in _iter_mappings(event):
            for candidate_key, value in mapping.items():
                if _normalize_field_name(candidate_key) != normalized_key:
                    continue
                if isinstance(value, str) and value.strip():
                    return value
    return None


def _values_for_keys(event: Mapping[str, Any], keys: Iterable[str]) -> list[Any]:
    normalized_keys = {_normalize_field_name(key) for key in keys}
    return list(_values_for_normalized_keys(event, normalized_keys))


def _values_for_normalized_keys(
    event: Mapping[str, Any],
    normalized_keys: Iterable[str],
) -> Iterable[Any]:
    accepted_keys = set(normalized_keys)
    for mapping in _iter_mappings(event):
        for key, value in mapping.items():
            if _normalize_field_name(key) in accepted_keys:
                yield value


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    queue: list[Any] = [value]
    seen: set[int] = set()

    while queue:
        current = queue.pop(0)
        current_id = id(current)
        if current_id in seen:
            continue
        seen.add(current_id)

        if isinstance(current, Mapping):
            yield current
            queue.extend(current.values())
        elif _is_sequence(current):
            queue.extend(current)


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
