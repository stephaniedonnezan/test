"""Build Linear issue title updates for the research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_KEYS = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "statusid",
    "stateid",
    "workflowstateid",
    "workflow_state_id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _first_text(event, ("newStatus", "new_status", "toStatus", "status", "state", "workflowState"))
    if not _same_status(new_status, TARGET_STATUS):
        return None

    title = _first_text(event, ("title", "name"))
    issue_id = _first_text(event, ("issueId", "issue_id", "identifier", "key", "id"))
    if not title or not issue_id:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title.strip()}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = _text_values_for_keys(event, ("trigger", "webhookType", "action", "type"))
    normalized_triggers = {_normalize_text(value) for value in trigger_values}

    if any(value in {"status changed", "statuschanged"} for value in normalized_triggers):
        return True

    if any(value in {"issue updated", "updated issue", "update", "updated"} for value in normalized_triggers):
        return _updated_fields_include_status(event)

    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        for field in _iter_values_for_key(event, key):
            if _field_list_includes_status(field):
                return True

    for key in ("changes", "updatedFrom", "updated_from"):
        for change in _iter_values_for_key(event, key):
            if _change_keys_include_status(change):
                return True

    return False


def _field_list_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in STATUS_FIELD_KEYS

    if isinstance(value, Iterable) and not isinstance(value, (bytes, str, Mapping)):
        return any(_field_list_includes_status(item) for item in value)

    if isinstance(value, Mapping):
        return _change_keys_include_status(value)

    return False


def _change_keys_include_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False

    return any(_normalize_key(key) in STATUS_FIELD_KEYS for key in value)


def _first_text(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        for value in _iter_values_for_key(event, key):
            text = _text_value(value)
            if text:
                return text
    return None


def _text_values_for_keys(event: Mapping[str, Any], keys: Iterable[str]) -> list[str]:
    values: list[str] = []
    for key in keys:
        for value in _iter_values_for_key(event, key):
            text = _text_value(value)
            if text:
                values.append(text)
    return values


def _iter_values_for_key(value: Any, target_key: str) -> Iterable[Any]:
    normalized_target = _normalize_key(target_key)

    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize_key(key) == normalized_target:
                yield item
            yield from _iter_values_for_key(item, target_key)
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, str)):
        for item in value:
            yield from _iter_values_for_key(item, target_key)


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _first_text(value, (key,))
            if text:
                return text

    return None


def _same_status(value: str | None, expected: str) -> bool:
    if not value:
        return False
    return _normalize_text(value) == expected


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _normalize_text(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).casefold().split()
    return " ".join(words)


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "", str(value)).casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
