"""Build Linear issue title updates for the Cursor research workflow."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATORS = re.compile(r"[\s_\-./]+")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    maps = list(_candidate_maps(event))
    if not _is_status_change_event(maps):
        return None

    if not any(_is_target_status(value) for value in _status_candidates(maps)):
        return None

    issue_id = _first_string(maps, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string(maps, ("title",))
    if not issue_id or not title:
        return None

    normalized_title = title.strip()
    if not normalized_title or _has_research_prefix(normalized_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {normalized_title}",
    }


def _candidate_maps(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield relevant nested payload maps in precedence order."""
    queue: list[Mapping[str, Any]] = [event]
    seen: set[int] = set()

    while queue:
        current = queue.pop(0)
        identity = id(current)
        if identity in seen:
            continue
        seen.add(identity)
        yield current

        for key in ("triggerContext", "data", "issue", "node", "object"):
            value = current.get(key)
            if isinstance(value, Mapping):
                queue.append(value)


def _is_status_change_event(maps: Iterable[Mapping[str, Any]]) -> bool:
    cached_maps = list(maps)
    trigger_values = [
        mapping.get(key)
        for mapping in cached_maps
        for key in ("trigger", "webhookType", "action", "type")
    ]

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    has_generic_update = any(_is_generic_issue_update(value) for value in trigger_values)
    return has_generic_update and any(_updated_fields_include_status(mapping) for mapping in cached_maps)


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_label(value)
    collapsed = normalized.replace(" ", "")
    return normalized in {
        "status changed",
        "status change",
        "issue status changed",
        "workflow state changed",
        "state changed",
    } or collapsed in {"statuschanged", "issuestatuschanged", "workflowstatechanged", "statechanged"}


def _is_generic_issue_update(value: Any) -> bool:
    normalized = _normalize_label(value)
    return normalized in {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "update issue",
        "updated issue",
    }


def _updated_fields_include_status(mapping: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _field_collection_includes_status(mapping.get(key)):
            return True

    for key in ("changes", "changed", "updated", "updatedFrom", "updated_from"):
        changes = mapping.get(key)
        if isinstance(changes, Mapping):
            if any(_is_status_field_name(field) for field in changes):
                return True
        elif _field_collection_includes_status(changes):
            return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field_name(field) for field in value)
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, Mapping):
                names = (item.get(key) for key in ("field", "fieldName", "name", "key"))
                if any(_is_status_field_name(name) for name in names):
                    return True
            elif _is_status_field_name(item):
                return True
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_label(value)
    collapsed = normalized.replace(" ", "")
    return collapsed in {"status", "state", "workflowstate", "statusid", "stateid", "workflowstateid"}


def _status_candidates(maps: Iterable[Mapping[str, Any]]) -> Iterable[Any]:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for mapping in maps:
        for key in explicit_keys:
            if key in mapping:
                yield mapping[key]

    for mapping in maps:
        yield from _status_values_from_changes(mapping)

    for mapping in maps:
        for key in fallback_keys:
            if key in mapping:
                yield mapping[key]


def _status_values_from_changes(mapping: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("changes", "changed", "updated"):
        changes = mapping.get(key)
        if isinstance(changes, Mapping):
            for field, value in changes.items():
                if _is_status_field_name(field):
                    yield from _new_values(value)
        elif isinstance(changes, Iterable) and not isinstance(changes, str):
            for item in changes:
                if isinstance(item, Mapping):
                    field_names = (item.get(field_key) for field_key in ("field", "fieldName", "name", "key"))
                    if any(_is_status_field_name(field_name) for field_name in field_names):
                        yield from _new_values(item)


def _new_values(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "new", "to", "after", "name"):
            if key in value:
                yield value[key]
    else:
        yield value


def _first_string(maps: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for mapping in maps:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _is_target_status(value: Any) -> bool:
    return _normalize_label(value) == TARGET_STATUS


def _normalize_label(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return _normalize_label(value[key])
        return ""
    if value is None:
        return ""

    text = str(value).strip()
    text = _CAMEL_BOUNDARY.sub(" ", text)
    text = _SEPARATORS.sub(" ", text)
    return text.casefold().strip()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(RESEARCH_PREFIX.casefold())


def main() -> int:
    """Read a JSON event from stdin and print the update action when needed."""
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
