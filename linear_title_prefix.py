"""Build Linear issue title updates for research status transitions.

The automation layer is responsible for applying the returned action to Linear.
This module only decides whether a status-change event should request a title
update and what the new title should be.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "state updated",
    "workflow state changed",
    "workflow state updated",
}

_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The accepted payloads include Cursor automation trigger contexts and Linear
    webhook-style nested issue objects. The title is prefixed at most once.
    """

    if not isinstance(event, Mapping):
        return None

    mappings = list(_walk_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _extract_new_status(mappings)
    if _normalize_token(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(mappings, _ISSUE_ID_KEYS)
    title = _extract_first_string(mappings, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child)


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    trigger_tokens = {
        normalized
        for value in _values_for_keys(mappings, _TRIGGER_KEYS)
        if (normalized := _normalize_token(_string_or_named_value(value)))
    }

    if trigger_tokens & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if trigger_tokens & _UPDATE_EVENTS:
        return _updated_fields_include_status(mappings)

    return False


def _updated_fields_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    for value in _values_for_keys(mappings, _UPDATED_FIELD_KEYS):
        for field_name in _walk_updated_field_names(value):
            normalized = _normalize_token(field_name)
            if normalized in {"status", "state", "workflow state"}:
                return True
    return False


def _walk_updated_field_names(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            if key in {"field", "name", "key"}:
                named_value = _string_or_named_value(child)
                if named_value is not None:
                    yield named_value
            yield from _walk_updated_field_names(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_updated_field_names(child)


def _extract_new_status(mappings: list[Mapping[str, Any]]) -> str | None:
    for value in _values_for_keys(mappings, _EXPLICIT_STATUS_KEYS):
        status = _string_or_named_value(value)
        if status:
            return status

    for value in _values_for_keys(mappings, _STATUS_KEYS):
        status = _string_or_named_value(value)
        if status:
            return status

    return None


def _extract_first_string(
    mappings: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for value in _values_for_keys(mappings, keys):
        text = _string_or_named_value(value)
        if text and text.strip():
            return text
    return None


def _values_for_keys(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Iterable[Any]:
    wanted = {key.lower() for key in keys}
    for mapping in mappings:
        for key, value in mapping.items():
            if key.lower() in wanted:
                yield value


def _string_or_named_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "displayName"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested

    return None


def _normalize_token(value: str | None) -> str | None:
    if value is None:
        return None

    text = value.strip()
    if not text:
        return None

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor\s+researching\b", title, flags=re.IGNORECASE) is not None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
