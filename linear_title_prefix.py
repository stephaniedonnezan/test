"""Build Linear issue title updates for Cursor research status changes.

The automation runtime can pass either Cursor's flat trigger context or a
native Linear webhook payload. This module keeps the decision small and
side-effect free: callers receive an update action only when an issue moved to
the "to research" status.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstateid",
    "statusid",
    "stateid",
}

_TRIGGER_KEYS = {
    "trigger",
    "action",
    "type",
    "event",
    "eventtype",
    "webhooktype",
}

_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "stateName",
    "workflowStateName",
)

_TITLE_KEYS = ("title", "issueTitle", "issue_title")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moved to research.

    The returned action is deliberately transport agnostic so the surrounding
    automation can decide how to apply it to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    mappings = list(_iter_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _find_new_status(mappings)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _find_first_text(mappings, _ISSUE_ID_KEYS)
    title = _find_first_text(mappings, _TITLE_KEYS)
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


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    """Yield mappings in a broad-first order so outer trigger metadata wins."""

    if not isinstance(value, Mapping):
        return

    queue: list[Mapping[str, Any]] = [value]
    seen: set[int] = set()
    while queue:
        current = queue.pop(0)
        identity = id(current)
        if identity in seen:
            continue
        seen.add(identity)
        yield current

        for nested_key in (
            "automation_trigger_info",
            "triggerContext",
            "trigger_context",
            "data",
            "issue",
            "node",
            "object",
        ):
            nested = current.get(nested_key)
            if isinstance(nested, Mapping):
                queue.append(nested)

        for nested_key in ("state", "status", "workflowState", "workflow_state"):
            nested = current.get(nested_key)
            if isinstance(nested, Mapping):
                queue.append(nested)


def _is_status_change_event(mappings: Sequence[Mapping[str, Any]]) -> bool:
    if _has_direct_status_changed_trigger(mappings):
        return True

    if _has_update_trigger(mappings) and _has_status_change_metadata(mappings):
        return True

    # Some webhook envelopes expose only field-change metadata.
    return _has_status_change_metadata(mappings) and _find_new_status(mappings) is not None


def _has_direct_status_changed_trigger(mappings: Sequence[Mapping[str, Any]]) -> bool:
    for value in _trigger_values(mappings):
        normalized = _normalize(value)
        if normalized in {"status changed", "status change", "issue status changed"}:
            return True
    return False


def _has_update_trigger(mappings: Sequence[Mapping[str, Any]]) -> bool:
    for value in _trigger_values(mappings):
        normalized = _normalize(value)
        if normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}:
            return True
    return False


def _trigger_values(mappings: Sequence[Mapping[str, Any]]) -> Iterable[Any]:
    for mapping in mappings:
        for key, value in mapping.items():
            if _canonical_key(key) in _TRIGGER_KEYS:
                yield value


def _has_status_change_metadata(mappings: Sequence[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("updatedFields", "updated_fields"):
            if _fields_include_status(mapping.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            changes = mapping.get(key)
            if isinstance(changes, Mapping) and _mapping_mentions_status_field(changes):
                return True

    return False


def _fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _canonical_key(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return _mapping_mentions_status_field(value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_fields_include_status(item) for item in value)

    return False


def _mapping_mentions_status_field(mapping: Mapping[str, Any]) -> bool:
    for key, value in mapping.items():
        if _canonical_key(key) in _STATUS_FIELD_NAMES:
            return True
        if isinstance(value, Mapping):
            field = value.get("field") or value.get("fieldName") or value.get("name")
            if _canonical_key(field) in _STATUS_FIELD_NAMES:
                return True
    return False


def _find_new_status(mappings: Sequence[Mapping[str, Any]]) -> str | None:
    for mapping in mappings:
        value = _find_first_text([mapping], _NEW_STATUS_KEYS)
        if value:
            return value

    for mapping in mappings:
        for key in ("changes", "changed"):
            value = _status_from_change_mapping(mapping.get(key))
            if value:
                return value

    for mapping in mappings:
        for key in ("updatedFields", "updated_fields"):
            value = _status_from_updated_fields(mapping.get(key))
            if value:
                return value

    for mapping in mappings:
        for key in ("state", "status", "workflowState", "workflow_state"):
            value = _status_name(mapping.get(key))
            if value:
                return value

    return _find_first_text(mappings, ("status", "state", "workflowState", "workflow_state"))


def _status_from_updated_fields(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _status_from_change_mapping(value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            if isinstance(item, Mapping):
                if _canonical_key(item.get("field") or item.get("fieldName")) in _STATUS_FIELD_NAMES:
                    status = _status_name(item.get("newValue") or item.get("new") or item.get("to"))
                    if status:
                        return status
                status = _status_from_change_mapping(item)
                if status:
                    return status

    return None


def _status_from_change_mapping(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, change in value.items():
        if _canonical_key(key) not in _STATUS_FIELD_NAMES:
            continue

        status = _status_name(change)
        if status:
            return status

    for change in value.values():
        if not isinstance(change, Mapping):
            continue
        field = change.get("field") or change.get("fieldName") or change.get("name")
        if _canonical_key(field) not in _STATUS_FIELD_NAMES:
            continue
        status = _status_name(change)
        if status:
            return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in (
            "newValue",
            "new_value",
            "to",
            "after",
            "value",
            "name",
            "title",
            "displayName",
        ):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
            if isinstance(nested, Mapping):
                status = _status_name(nested)
                if status:
                    return status

    return None


def _find_first_text(mappings: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    canonical_keys = [_canonical_key(key) for key in keys]
    for canonical_key in canonical_keys:
        for mapping in mappings:
            for key, value in mapping.items():
                if _canonical_key(key) == canonical_key and isinstance(value, str):
                    stripped = value.strip()
                    if stripped:
                        return stripped
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = _CAMEL_BOUNDARY.sub(" ", str(value))
    text = _NON_ALNUM.sub(" ", text.lower())
    return " ".join(text.split())


def _canonical_key(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def main() -> int:
    """Read a JSON payload from stdin and print the title update if needed."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 2

    update = build_issue_title_update(payload)
    if update is None:
        return 1

    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
