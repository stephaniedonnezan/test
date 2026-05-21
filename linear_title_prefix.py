"""Build Linear issue-title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_words(_extract_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _first_text(_issue_sources(event), ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(_issue_sources(event), ("title", "name"))
    if issue_id is None or title is None:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


handle_issue_status_changed = build_issue_title_update


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_kinds = {_normalize_words(value) for value in _event_type_values(event)}
    direct_status_change_kinds = {
        "status change",
        "status changed",
        "status update",
        "status updated",
        "state change",
        "state changed",
        "workflow state change",
        "workflow state changed",
    }

    if event_kinds & direct_status_change_kinds:
        return True

    issue_update_kinds = {"update", "updated", "issue update", "issue updated", "updated issue"}
    has_issue_update = bool(event_kinds & issue_update_kinds) and (
        any("issue" in kind for kind in event_kinds)
        or _mapping_at(event, "issue") is not None
        or _mapping_at(_mapping_at(event, "data"), "issue") is not None
        or _mapping_at(_mapping_at(event, "payload"), "issue") is not None
    )

    return has_issue_update and any(_is_status_field_name(name) for name in _changed_field_names(event))


def _event_type_values(event: Mapping[str, Any]) -> Iterable[Any]:
    keys = (
        "trigger",
        "triggerType",
        "trigger_type",
        "webhookType",
        "webhook_type",
        "action",
        "type",
        "eventType",
        "event_type",
    )

    for source in _metadata_sources(event):
        for key in keys:
            value = _value_at(source, key)
            if value is not None:
                yield value


def _changed_field_names(event: Mapping[str, Any]) -> Iterable[Any]:
    field_keys = (
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
        "updatedFrom",
        "updated_from",
        "changes",
    )

    for source in _metadata_sources(event):
        for key in field_keys:
            yield from _field_names_from_value(_value_at(source, key))


def _field_names_from_value(value: Any) -> Iterable[Any]:
    if value is None:
        return

    if isinstance(value, Mapping):
        yield from value.keys()
        for key in ("field", "fieldName", "field_name", "name", "key", "property", "path"):
            nested_value = _value_at(value, key)
            if nested_value is not None:
                yield nested_value
        return

    if isinstance(value, str):
        yield value
        return

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, Mapping):
                yield from _field_names_from_value(item)
            else:
                yield item


def _is_status_field_name(value: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", _normalize_words(value))
    return normalized in {
        "status",
        "statusid",
        "state",
        "stateid",
        "workflowstate",
        "workflowstateid",
    }


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for source in _status_sources(event):
        value = _first_status_text([source], explicit_keys)
        if value is not None:
            return value

    return _first_status_text(_status_sources(event), fallback_keys)


def _metadata_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "trigger_context", "context", "payload", "data", "issue"):
        value = _mapping_at(event, key)
        if value is not None:
            sources.append(value)

    data = _mapping_at(event, "data")
    data_issue = _mapping_at(data, "issue")
    if data_issue is not None:
        sources.append(data_issue)

    payload = _mapping_at(event, "payload")
    payload_issue = _mapping_at(payload, "issue")
    if payload_issue is not None:
        sources.append(payload_issue)

    return _dedupe_mappings(sources)


def _status_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    for key in ("triggerContext", "trigger_context", "context", "payload"):
        value = _mapping_at(event, key)
        if value is not None:
            sources.append(value)

    sources.append(event)

    data = _mapping_at(event, "data")
    if data is not None:
        sources.append(data)
        data_issue = _mapping_at(data, "issue")
        if data_issue is not None:
            sources.append(data_issue)

    issue = _mapping_at(event, "issue")
    if issue is not None:
        sources.append(issue)

    return _dedupe_mappings(sources)


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []

    for key in ("triggerContext", "trigger_context", "context", "payload"):
        value = _mapping_at(event, key)
        if value is not None:
            nested_issue = _mapping_at(value, "issue")
            if nested_issue is not None:
                sources.append(nested_issue)
            sources.append(value)

    data = _mapping_at(event, "data")
    if data is not None:
        data_issue = _mapping_at(data, "issue")
        if data_issue is not None:
            sources.append(data_issue)
        sources.append(data)

    issue = _mapping_at(event, "issue")
    if issue is not None:
        sources.append(issue)

    sources.append(event)
    return _dedupe_mappings(sources)


def _first_status_text(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        for key in keys:
            value = _value_at(source, key)
            if isinstance(value, Mapping):
                value = _value_at(value, "name") or _value_at(value, "title") or _value_at(value, "label")
            if isinstance(value, str) and value.strip():
                return value
    return None


def _first_text(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        for key in keys:
            value = _value_at(source, key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _mapping_at(source: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(source, Mapping):
        return None
    value = _value_at(source, key)
    return value if isinstance(value, Mapping) else None


def _value_at(source: Mapping[str, Any], key: str) -> Any:
    if key in source:
        return source[key]

    normalized_key = _normalize_key(key)
    for existing_key, value in source.items():
        if isinstance(existing_key, str) and _normalize_key(existing_key) == normalized_key:
            return value
    return None


def _dedupe_mappings(sources: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    unique_sources: list[Mapping[str, Any]] = []
    for source in sources:
        identity = id(source)
        if identity not in seen:
            seen.add(identity)
            unique_sources.append(source)
    return unique_sources


def _has_research_prefix(title: str) -> bool:
    normalized_title = _normalize_words(title)
    normalized_prefix = _normalize_words(TITLE_PREFIX)
    return normalized_title == normalized_prefix or normalized_title.startswith(f"{normalized_prefix} ")


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value).lower()


def main() -> int:
    """Read a JSON event from stdin and print a title-update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
