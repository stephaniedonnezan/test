"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "event", "eventType")
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
)
_CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_TITLE_KEYS = ("title", "name", "summary")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action for Linear issues moved to research.

    The Cursor automation payload can provide issue data as a flat
    ``triggerContext`` object, while Linear webhooks commonly nest the issue
    under ``data`` or ``issue``. This function supports both shapes and keeps
    the decision side-effect free for callers/tests.
    """

    if not isinstance(event, Mapping):
        return None

    mappings = _collect_mappings(event)
    if not _is_status_change(mappings):
        return None

    new_status = _extract_new_status(mappings)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_mappings = _collect_issue_mappings(event)
    title = _extract_first_text(issue_mappings, _TITLE_KEYS)
    issue_id = _extract_first_text(issue_mappings, _ISSUE_ID_KEYS)
    if not title or not issue_id:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _collect_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect useful payload scopes, with outer metadata before issue fields."""

    mappings: list[Mapping[str, Any]] = [event]
    for path in (
        ("automation_trigger_info",),
        ("automation_trigger_info", "triggerContext"),
        ("triggerContext",),
        ("data",),
        ("data", "issue"),
        ("issue",),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping) and value not in mappings:
            mappings.append(value)
    return mappings


def _collect_issue_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect issue-bearing scopes before generic webhook metadata scopes."""

    mappings: list[Mapping[str, Any]] = []
    for path in (
        ("automation_trigger_info", "triggerContext"),
        ("triggerContext",),
        ("data", "issue"),
        ("issue",),
        ("data",),
        (),
        ("automation_trigger_info",),
    ):
        value = event if not path else _get_path(event, path)
        if isinstance(value, Mapping) and value not in mappings:
            mappings.append(value)
    return mappings


def _get_path(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _is_status_change(mappings: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        text
        for mapping in mappings
        for key in _TRIGGER_KEYS
        if (text := _coerce_text(mapping.get(key)))
    ]

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(_is_issue_update(value) for value in trigger_values):
        return _updated_fields_include_status(mappings)

    return False


def _is_direct_status_change(value: str) -> bool:
    normalized = _normalize_text(value)
    compact = normalized.replace(" ", "")
    return compact in {"statuschanged", "statuschange", "statechanged", "statechange"}


def _is_issue_update(value: str) -> bool:
    normalized = _normalize_text(value)
    compact = normalized.replace(" ", "")
    return compact in {"issueupdated", "updatedissue", "update", "updated"}


def _updated_fields_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        if _fields_include_status(mapping.get("updatedFields")):
            return True
        if _fields_include_status(mapping.get("changedFields")):
            return True
        if _changes_include_status(mapping.get("changes")):
            return True
    return False


def _fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize_field_name(key) in _STATUS_FIELD_NAMES for key in value)

    if isinstance(value, list | tuple | set):
        return any(_fields_include_status(item) for item in value)

    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_normalize_field_name(key) in _STATUS_FIELD_NAMES for key in value)

    if isinstance(value, list | tuple | set):
        for item in value:
            if isinstance(item, Mapping):
                field_name = item.get("field") or item.get("name") or item.get("key")
                if _normalize_field_name(field_name) in _STATUS_FIELD_NAMES:
                    return True
            elif _fields_include_status(item):
                return True

    return False


def _extract_new_status(mappings: list[Mapping[str, Any]]) -> str | None:
    for mapping in mappings:
        for key in _EXPLICIT_NEW_STATUS_KEYS:
            text = _coerce_text(mapping.get(key))
            if text:
                return text

    for mapping in mappings:
        for changes_key in ("changes", "updatedFields", "changedFields"):
            status = _status_from_changes(mapping.get(changes_key))
            if status:
                return status

    for mapping in mappings:
        for key in _CURRENT_STATUS_KEYS:
            text = _coerce_text(mapping.get(key))
            if text:
                return text

    return None


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _normalize_field_name(key) not in _STATUS_FIELD_NAMES:
                continue
            if isinstance(change, Mapping):
                return (
                    _coerce_text(change.get("to"))
                    or _coerce_text(change.get("new"))
                    or _coerce_text(change.get("newValue"))
                    or _coerce_text(change.get("after"))
                )
            return _coerce_text(change)

    if isinstance(value, list | tuple | set):
        for item in value:
            if not isinstance(item, Mapping):
                continue
            field_name = item.get("field") or item.get("name") or item.get("key")
            if _normalize_field_name(field_name) not in _STATUS_FIELD_NAMES:
                continue
            status = (
                _coerce_text(item.get("to"))
                or _coerce_text(item.get("new"))
                or _coerce_text(item.get("newValue"))
                or _coerce_text(item.get("after"))
                or _coerce_text(item.get("value"))
            )
            if status:
                return status

    return None


def _extract_first_text(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for mapping in mappings:
        for key in keys:
            text = _coerce_text(mapping.get(key))
            if text:
                return text
    return None


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "id", "identifier"):
            text = _coerce_text(value.get(key))
            if text:
                return text

    return None


def _normalize_text(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
