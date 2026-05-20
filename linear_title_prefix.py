"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "workflow status",
    "workflowstatus",
}
_UPDATE_EVENT_NAMES = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _new_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(event)
    title = _issue_title(event)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = _values_for_keys(event, {"trigger", "webhookType", "action", "type"})
    if any(_is_status_changed_value(value) for value in trigger_values):
        return True

    if any(_normalize(value) in _UPDATE_EVENT_NAMES for value in trigger_values):
        return _updated_fields_include_status(event)

    return False


def _is_status_changed_value(value: Any) -> bool:
    normalized = _normalize(value)
    if not normalized:
        return False

    return (
        normalized in {"status changed", "state changed", "workflow state changed"}
        or ("status" in normalized and "chang" in normalized)
        or ("state" in normalized and "chang" in normalized)
    )


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for source in _all_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = source.get(key)
            if _fields_include_status(fields):
                return True

        updated_from = source.get("updatedFrom") or source.get("updated_from")
        if isinstance(updated_from, Mapping) and _fields_include_status(updated_from.keys()):
            return True

    return False


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, Mapping):
        iterable = fields.keys()
    elif _is_sequence(fields):
        iterable = fields
    else:
        return False

    return any(_normalize(field) in _STATUS_FIELD_NAMES for field in iterable)


def _new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    for source in _metadata_sources(event):
        status = _first_text(source, explicit_keys)
        if status:
            return status

    for source in _issue_sources(event) + _metadata_sources(event):
        status = _first_text(source, status_keys)
        if status:
            return status

    return None


def _issue_id(event: Mapping[str, Any]) -> str | None:
    return _first_text_from_sources(
        _issue_sources(event) + _metadata_sources(event),
        ("id", "issueId", "issue_id", "identifier"),
    )


def _issue_title(event: Mapping[str, Any]) -> str | None:
    return _first_text_from_sources(_issue_sources(event) + _metadata_sources(event), ("title",))


def _metadata_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    for key in ("triggerContext", "trigger_context"):
        value = event.get(key)
        if isinstance(value, Mapping):
            sources.append(value)

    sources.append(event)

    data = event.get("data")
    if isinstance(data, Mapping):
        sources.append(data)

    return _unique_mappings(sources)


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []

    for parent in _metadata_sources(event):
        for key in ("issue", "data", "payload"):
            value = parent.get(key)
            if isinstance(value, Mapping):
                nested_issue = value.get("issue")
                if isinstance(nested_issue, Mapping):
                    sources.append(nested_issue)
                sources.append(value)

    for key in ("issue", "data", "payload"):
        value = event.get(key)
        if isinstance(value, Mapping):
            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                sources.append(nested_issue)
            sources.append(value)

    return _unique_mappings(sources)


def _all_mappings(value: Any) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            mappings.append(item)
            for child in item.values():
                visit(child)
        elif _is_sequence(item):
            for child in item:
                visit(child)

    visit(value)
    return _unique_mappings(mappings)


def _values_for_keys(event: Mapping[str, Any], keys: set[str]) -> list[Any]:
    values: list[Any] = []
    for source in _all_mappings(event):
        for key, value in source.items():
            if key in keys:
                values.append(value)

    return values


def _first_text_from_sources(sources: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for source in sources:
        value = _first_text(source, keys)
        if value:
            return value

    return None


def _first_text(source: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        if key in source:
            value = _text_value(source[key])
            if value:
                return value

    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    return None


def _normalize(value: Any) -> str:
    text = _text_value(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _unique_mappings(mappings: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    unique: list[Mapping[str, Any]] = []
    for mapping in mappings:
        mapping_id = id(mapping)
        if mapping_id not in seen:
            unique.append(mapping)
            seen.add(mapping_id)

    return unique


def main() -> int:
    """Read a JSON event from stdin and write the resulting action as JSON."""

    event = json.loads(sys.stdin.read() or "{}")
    json.dump(build_issue_title_update(event), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
