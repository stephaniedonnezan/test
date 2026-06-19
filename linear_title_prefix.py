"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
    "stateName",
    "state_name",
    "newWorkflowState",
    "new_workflow_state",
    "workflowStateName",
    "workflow_state_name",
)
_FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    sources = list(_priority_sources(event))
    if not _is_status_change_event(sources):
        return None

    status = _extract_new_status(sources)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    title = _extract_string(sources, ("title",))
    issue_id = _extract_issue_id(sources)
    if not title or not issue_id:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _priority_sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload containers from most explicit to most nested."""

    yield event

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _is_status_change_event(sources: Iterable[Mapping[str, Any]]) -> bool:
    source_list = list(sources)
    trigger_names = {
        _normalize_words(source[key])
        for source in source_list
        for key in _TRIGGER_KEYS
        if key in source
    }

    if trigger_names & _DIRECT_STATUS_TRIGGERS:
        return True

    if trigger_names & _GENERIC_UPDATE_TRIGGERS:
        return any(_is_status_field(field) for field in _updated_field_names(source_list))

    return False


def _extract_new_status(sources: Iterable[Mapping[str, Any]]) -> str | None:
    source_list = list(sources)

    for source in source_list:
        value = _extract_from_source(source, _EXPLICIT_STATUS_KEYS)
        if value:
            return value

    changed_status = _extract_status_from_changes(source_list)
    if changed_status:
        return changed_status

    for source in source_list:
        value = _extract_from_source(source, _FALLBACK_STATUS_KEYS)
        if value:
            return value

    return None


def _extract_from_source(source: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        if key in source:
            value = _stringify_value(source[key])
            if value:
                return value
    return None


def _extract_status_from_changes(sources: Iterable[Mapping[str, Any]]) -> str | None:
    for source in sources:
        value = _status_value_from_change_container(source.get("changes"))
        if value:
            return value
    return None


def _status_value_from_change_container(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if not _is_status_field(str(key)):
                continue
            status_value = _status_value_from_change(change)
            if status_value:
                return status_value
    elif isinstance(value, list):
        for item in value:
            status_value = _status_value_from_change(item)
            if status_value:
                return status_value
    return None


def _status_value_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        field_name = change.get("field") or change.get("name") or change.get("key")
        if field_name and not _is_status_field(str(field_name)):
            return None
        for key in ("to", "new", "newValue", "new_value", "after", "value"):
            if key in change:
                value = _stringify_value(change[key])
                if value:
                    return value
    return _stringify_value(change)


def _updated_field_names(sources: Iterable[Mapping[str, Any]]) -> Iterable[str]:
    for source in sources:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            yield from _field_names(source.get(key))
        yield from _field_names(source.get("changes"))
        yield from _field_names(source.get("updatedFrom"))
        yield from _field_names(source.get("updated_from"))


def _field_names(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        yield from (str(key) for key in value)
        field = value.get("field") or value.get("name") or value.get("key")
        if field:
            yield str(field)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                field = item.get("field") or item.get("name") or item.get("key")
                if field:
                    yield str(field)
                else:
                    yield from (str(key) for key in item)
            else:
                yield str(item)
    elif value:
        yield str(value)


def _extract_string(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        value = _extract_from_source(source, keys)
        if value:
            return value
    return None


def _extract_issue_id(sources: Iterable[Mapping[str, Any]]) -> str | None:
    source_list = list(sources)
    explicit_id = _extract_string(source_list, _ISSUE_ID_KEYS)
    if explicit_id:
        return explicit_id
    return _extract_string(source_list, ("id",))


def _stringify_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "id", "identifier"):
            if key in value:
                nested_value = _stringify_value(value[key])
                if nested_value:
                    return nested_value
        return None
    if isinstance(value, (list, tuple, set)):
        return None
    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _is_status_field(field: str) -> bool:
    normalized = _normalize_words(field)
    return normalized in _STATUS_FIELD_NAMES


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
