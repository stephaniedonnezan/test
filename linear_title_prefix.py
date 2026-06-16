"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "issueTitle", "issue_title")
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "eventType")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_CHANGE_KEYS = (
    "changes",
    "changed",
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "updatedFrom",
    "updated_from",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(event, _ID_KEYS)
    title = _extract_first_text(event, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    if _has_status_changed_trigger(event):
        return True

    return _has_status_field_marker(event)


def _has_status_changed_trigger(event: Mapping[str, Any]) -> bool:
    for item in _walk_mappings(event):
        for key in _TRIGGER_KEYS:
            marker = _compact_words(item.get(key))
            if marker in {"statuschanged", "statuschange"}:
                return True
    return False


def _has_status_field_marker(event: Mapping[str, Any]) -> bool:
    for item in _walk_mappings(event):
        for key in _CHANGE_KEYS:
            if _change_mentions_status(item.get(key)):
                return True
    return False


def _change_mentions_status(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _is_status_field(key):
                return True
            if key in {"field", "name", "key", "property", "attribute"} and _is_status_field(
                nested_value
            ):
                return True
            if _change_mentions_status(nested_value):
                return True
        return False

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        return any(_change_mentions_status(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    return _compact_words(value) in {"status", "state", "workflowstate"}


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for keys in (_EXPLICIT_STATUS_KEYS,):
        value = _extract_first_text(event, keys)
        if value:
            return value

    value = _extract_status_from_changes(event)
    if value:
        return value

    return _extract_first_text(event, _STATUS_KEYS)


def _extract_status_from_changes(event: Mapping[str, Any]) -> str | None:
    for item in _walk_mappings(event):
        for key in _CHANGE_KEYS:
            value = _status_value_from_change(item.get(key))
            if value:
                return value
    return None


def _status_value_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _is_status_field(key):
                return _coerce_text(_new_value_from_change_payload(nested_value))

            if key in {"field", "name", "key", "property", "attribute"} and _is_status_field(
                nested_value
            ):
                candidate = _new_value_from_change_payload(value)
                if candidate:
                    return _coerce_text(candidate)

            candidate = _status_value_from_change(nested_value)
            if candidate:
                return candidate

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        for item in value:
            candidate = _status_value_from_change(item)
            if candidate:
                return candidate

    return None


def _new_value_from_change_payload(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value

    for key in (
        "newValue",
        "new_value",
        "new",
        "after",
        "to",
        "current",
        "value",
        "name",
    ):
        candidate = value.get(key)
        if candidate is not None:
            return candidate

    return None


def _extract_first_text(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for item in _preferred_issue_mappings(event):
        for key in keys:
            value = item.get(key)
            text = _coerce_text(value)
            if text:
                return text
    return None


def _preferred_issue_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in mappings:
            mappings.append(value)

    add(event.get("triggerContext"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    add(event)

    for item in _walk_mappings(event):
        add(item)

    return mappings


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested_value in value.values():
            yield from _walk_mappings(nested_value)
        return

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        for item in value:
            yield from _walk_mappings(item)


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            text = _coerce_text(value.get(key))
            if text:
                return text

    return None


def _normalize_words(value: Any) -> str | None:
    text = _coerce_text(value)
    if not text:
        return None

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _compact_words(value: Any) -> str:
    normalized = _normalize_words(value)
    return "" if normalized is None else normalized.replace(" ", "")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(payload)
    if update is None:
        return 0

    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
