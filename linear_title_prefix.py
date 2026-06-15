"""Build Linear issue title updates for research status transitions.

The automation runner can pass either a compact Cursor trigger context or the
raw-ish Linear webhook shape.  This module keeps the matching logic local and
side-effect free: callers can apply the returned action through their Linear
client, or do nothing when ``None`` is returned.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_TRIGGER_FIELD_NAMES = {"trigger", "webhooktype", "webhook_type", "action", "type"}
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
)
_CHANGE_TARGET_KEYS = (
    "to",
    "new",
    "after",
    "newValue",
    "new_value",
    "name",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves to ``to research``.

    The returned dict is deliberately small and serializable:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    ``None`` means the event is not relevant or lacks enough issue data.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_issue_title(event)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _already_prefixed(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for mapping in _iter_mappings(event)
        for key, value in mapping.items()
        if _normalize_key(key) in _TRIGGER_FIELD_NAMES
    ]

    if any(_normalize_text(value) == "status changed" for value in trigger_values):
        return True

    is_issue_update = any(
        _normalize_text(value) in {"issue updated", "updated issue", "update"}
        for value in trigger_values
    )
    return is_issue_update and _mentions_status_field(event)


def _mentions_status_field(event: Mapping[str, Any]) -> bool:
    for mapping in _iter_mappings(event):
        updated_fields = _value_for_any_key(mapping, ("updatedFields", "updated_fields"))
        if updated_fields is not None and _contains_status_field_name(updated_fields):
            return True

        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize_key(key) in _STATUS_FIELD_NAMES for key in changes):
                return True

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for key in _EXPLICIT_STATUS_KEYS:
        value = _first_nested_value_for_key(event, key)
        status = _coerce_name(value)
        if status:
            return status

    change_status = _status_from_changes(event)
    if change_status:
        return change_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _first_nested_value_for_key(event, key)
        status = _coerce_name(value)
        if status:
            return status

    return None


def _status_from_changes(event: Mapping[str, Any]) -> str | None:
    for mapping in _iter_mappings(event):
        changes = mapping.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for field_name, change in changes.items():
            if _normalize_key(field_name) not in _STATUS_FIELD_NAMES:
                continue

            if isinstance(change, Mapping):
                for key in _CHANGE_TARGET_KEYS:
                    status = _coerce_name(_value_for_any_key(change, (key,)))
                    if status:
                        return status
            else:
                status = _coerce_name(change)
                if status:
                    return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        trigger_id = _coerce_name(trigger_context.get("id"))
        if trigger_id:
            return trigger_id

    for key in ("issueId", "issue_id", "identifier", "key"):
        value = _first_nested_value_for_key(event, key)
        issue_id = _coerce_name(value)
        if issue_id:
            return issue_id

    for mapping in _iter_mappings(event):
        if "title" in mapping:
            issue_id = _coerce_name(mapping.get("id"))
            if issue_id:
                return issue_id

    return None


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        trigger_title = _coerce_name(trigger_context.get("title"))
        if trigger_title:
            return trigger_title

    for key in ("issueTitle", "issue_title", "title"):
        value = _first_nested_value_for_key(event, key)
        title = _coerce_name(value)
        if title:
            return title

    return None


def _already_prefixed(title: str) -> bool:
    return title.lstrip().lower().startswith(TITLE_PREFIX.lower())


def _first_nested_value_for_key(value: Any, wanted_key: str) -> Any:
    wanted = _normalize_key(wanted_key)
    for mapping in _iter_mappings(value):
        for key, candidate in mapping.items():
            if _normalize_key(key) == wanted:
                return candidate
    return None


def _value_for_any_key(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    wanted = {_normalize_key(key) for key in keys}
    for key, value in mapping.items():
        if _normalize_key(key) in wanted:
            return value
    return None


def _contains_status_field_name(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(
            _contains_status_field_name(key) or _contains_status_field_name(item)
            for key, item in value.items()
        )
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field_name(item) for item in value)
    return False


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for item in value.values():
            yield from _iter_mappings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_mappings(item)


def _coerce_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "displayName", "display_name", "key", "id"):
            nested = _coerce_name(_value_for_any_key(value, (key,)))
            if nested:
                return nested
    return None


def _normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    spaced = re.sub(r"[_\-/]+", " ", spaced)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(spaced.lower().split())


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON: {exc.msg}"}), file=sys.stderr)
        return 2

    print(json.dumps(build_issue_title_update(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
