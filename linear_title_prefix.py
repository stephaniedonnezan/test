"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newStateName",
    "new_state_name",
    "statusName",
    "stateName",
)
_TRIGGER_KEYS = ("trigger", "event", "eventType", "webhookType", "action", "type")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changedProperties",
    "updatedFrom",
    "updated_from",
)
_STATUS_FIELD_KEYS = {
    "status",
    "state",
    "workflowstate",
    "statusid",
    "stateid",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _find_new_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _find_issue_id(event)
    title = _find_issue_title(event)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for value in _trigger_values(event):
        normalized = _normalize_text(value)
        words = set(normalized.split())
        if "status" in words and words & {"change", "changed"}:
            return True

    return _is_issue_update_event(event) and _updated_fields_include_status(event)


def _is_issue_update_event(event: Mapping[str, Any]) -> bool:
    for value in _trigger_values(event):
        normalized = _normalize_text(value)
        words = set(normalized.split())
        if "update" in words or "updated" in words:
            return True
    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for mapping in _walk_mappings(event):
        for key in _UPDATED_FIELD_KEYS:
            if key in mapping and any(_is_status_field_name(field) for field in _field_names(mapping[key])):
                return True
    return False


def _trigger_values(event: Mapping[str, Any]) -> Iterable[str]:
    for mapping in _walk_mappings(event):
        for key in _TRIGGER_KEYS:
            value = _string_value(mapping.get(key))
            if value:
                yield value


def _find_new_status(event: Mapping[str, Any]) -> str | None:
    for source in _priority_sources(event):
        for key in _NEW_STATUS_KEYS:
            value = _string_value(source.get(key))
            if value:
                return value

    for source in _priority_sources(event):
        value = _string_value(source.get("status"))
        if value:
            return value

        for key in ("state", "workflowState", "workflow_state", "status"):
            value = _name_from_value(source.get(key))
            if value:
                return value

    return None


def _find_issue_id(event: Mapping[str, Any]) -> str | None:
    for source in _priority_sources(event):
        for key in ("issueId", "issue_id", "id", "identifier"):
            value = _string_value(source.get(key))
            if value:
                return value
    return None


def _find_issue_title(event: Mapping[str, Any]) -> str | None:
    for source in _priority_sources(event):
        value = _string_value(source.get("title"))
        if value:
            return value
    return None


def _priority_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    paths = (
        ("triggerContext",),
        (),
        ("data",),
        ("data", "issue"),
        ("issue",),
    )
    sources: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    for path in paths:
        source = _mapping_at_path(event, path)
        if source is None or id(source) in seen:
            continue
        seen.add(id(source))
        sources.append(source)

    return sources


def _mapping_at_path(root: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    current: Any = root
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child)


def _field_names(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        yield from (str(key) for key in value.keys())
    elif isinstance(value, Iterable):
        for item in value:
            yield from _field_names(item)


def _is_status_field_name(value: str) -> bool:
    return _normalize_key(value) in _STATUS_FIELD_KEYS


def _name_from_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _string_value(value.get("name") or value.get("title"))
    return _string_value(value)


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
    elif isinstance(value, (int, float)):
        stripped = str(value).strip()
    else:
        return None
    return stripped or None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().casefold()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", value).casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
