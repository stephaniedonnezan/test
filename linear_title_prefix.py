"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "workflow status",
    "state id",
    "status id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_issue_title(event)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.lower().startswith(RESEARCH_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = []
    for container in _iter_contexts(event):
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            value = container.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize_text(value))

    if any(value in {"status changed", "status change", "statuschanged"} for value in trigger_values):
        return True

    if any("update" in value or value == "issue updated" for value in trigger_values):
        return _has_status_change_marker(event)

    return _has_explicit_new_status(event)


def _has_explicit_new_status(event: Mapping[str, Any]) -> bool:
    for container in _iter_contexts(event):
        if any(key in container for key in ("newStatus", "new_status", "toStatus", "to_status")):
            return True
    return False


def _has_status_change_marker(event: Mapping[str, Any]) -> bool:
    for container in _iter_contexts(event):
        if _updated_fields_include_status(container.get("updatedFields")):
            return True
        if _updated_fields_include_status(container.get("updated_fields")):
            return True
        if _changes_include_status(container.get("changes")):
            return True
        if _changes_include_status(container.get("updatedFrom")):
            return True
        if _changes_include_status(container.get("updated_from")):
            return True
    return False


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, str) and _is_status_field(item):
                return True
            if isinstance(item, Mapping):
                field_name = item.get("field") or item.get("name") or item.get("key")
                if isinstance(field_name, str) and _is_status_field(field_name):
                    return True
    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _is_status_field(key):
                return True
            if isinstance(change, Mapping):
                field_name = change.get("field") or change.get("name") or change.get("key")
                if isinstance(field_name, str) and _is_status_field(field_name):
                    return True
        return False

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for change in value:
            if not isinstance(change, Mapping):
                continue
            field_name = change.get("field") or change.get("name") or change.get("key")
            if isinstance(field_name, str) and _is_status_field(field_name):
                return True
    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for container in _iter_contexts(event):
        for key in ("newStatus", "new_status", "toStatus", "to_status", "statusName", "status_name"):
            status = _coerce_name(container.get(key))
            if status:
                return status

    for container in _iter_contexts(event):
        status = _status_from_changes(container.get("changes"))
        if status:
            return status
        status = _status_from_changes(container.get("updatedFields"))
        if status:
            return status
        status = _status_from_changes(container.get("updated_fields"))
        if status:
            return status

    for container in _iter_contexts(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _coerce_name(container.get(key))
            if status:
                return status

    return None


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _is_status_field(key):
                status = _coerce_change_target(change)
                if status:
                    return status
            if isinstance(change, Mapping):
                field_name = change.get("field") or change.get("name") or change.get("key")
                if isinstance(field_name, str) and _is_status_field(field_name):
                    status = _coerce_change_target(change)
                    if status:
                        return status
        return None

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for change in value:
            if not isinstance(change, Mapping):
                continue
            field_name = change.get("field") or change.get("name") or change.get("key")
            if isinstance(field_name, str) and _is_status_field(field_name):
                status = _coerce_change_target(change)
                if status:
                    return status
    return None


def _coerce_change_target(change: Any) -> str | None:
    if not isinstance(change, Mapping):
        return _coerce_name(change)

    for key in ("to", "after", "newValue", "new_value", "value", "name"):
        status = _coerce_name(change.get(key))
        if status:
            return status
    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for container in _iter_issue_containers(event):
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    for container in _iter_issue_containers(event):
        for key in ("title", "name"):
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _iter_issue_containers(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            yield data_issue
        yield data

    # Keep the top-level payload last so webhook ids do not outrank issue ids.
    yield event


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            yield data_issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _coerce_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested_value = value.get(key)
            if isinstance(nested_value, str) and nested_value.strip():
                return nested_value.strip()
    return None


def _is_status_field(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized in _STATUS_FIELD_NAMES or normalized.endswith(" status")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
