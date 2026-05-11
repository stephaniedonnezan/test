"""Helpers for adding a Cursor research marker to Linear issue titles."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATORS = re.compile(r"[\s_\-/]+")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Build a title-update action for Linear issues moved to To Research.

    The Cursor automation payloads used by Linear can be flat or nested under
    keys such as ``triggerContext``, ``data``, or ``issue``. This function keeps
    the public contract small: return the desired update action, or ``None``
    when the event is not a status transition into the research state.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _event_contexts(event)
    if not _is_status_change(contexts):
        return None

    status = _status_value(contexts)
    if _normalize_words(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(contexts, ("title",))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Compatibility alias for automation entrypoints using handler naming."""

    return build_issue_title_update(event)


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue/event mappings in precedence order."""

    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping_at(event, "triggerContext")
    data = _mapping_at(event, "data")
    issue = _mapping_at(event, "issue")

    _append_mapping(contexts, trigger_context)
    if data is not None:
        _append_mapping(contexts, _mapping_at(data, "issue"))
        _append_mapping(contexts, data)
    _append_mapping(contexts, issue)
    _append_mapping(contexts, event)

    return contexts


def _is_status_change(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "action", "type", "eventType"):
            if _is_status_change_marker(context.get(key)):
                return True

        if _is_issue_updated_marker(context) and _updated_fields_include_status(context):
            return True

    return False


def _is_status_change_marker(value: Any) -> bool:
    normalized = _normalize_words(value)
    return normalized in {"status changed", "status change"}


def _is_issue_updated_marker(context: Mapping[str, Any]) -> bool:
    for key in ("trigger", "action", "type", "eventType"):
        normalized = _normalize_words(context.get(key))
        if normalized in {"issue updated", "updated issue", "issue update", "update issue"}:
            return True
    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    fields = context.get("updatedFields")
    if fields is None:
        fields = context.get("updated_fields")

    if isinstance(fields, Mapping):
        candidates = fields.keys()
    elif isinstance(fields, str):
        candidates = [fields]
    elif isinstance(fields, Iterable):
        candidates = fields
    else:
        return False

    for field in candidates:
        if isinstance(field, Mapping):
            field_name = field.get("name") or field.get("field") or field.get("key")
        else:
            field_name = field

        if _normalize_words(field_name) in {"status", "state", "workflow state"}:
            return True

    return False


def _status_value(contexts: Iterable[Mapping[str, Any]]) -> Any:
    for key in ("newStatus", "new_status", "status", "stateName", "state_name"):
        value = _first_value(contexts, (key,))
        if value is not None:
            return value

    for context in contexts:
        for key in ("state", "workflowState", "workflow_state"):
            nested = _mapping_at(context, key)
            if nested is not None:
                value = nested.get("name")
                if value is not None:
                    return value

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    value = _first_value(contexts, keys)
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _first_value(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Any:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if value is not None:
                return value
    return None


def _mapping_at(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _append_mapping(
    contexts: list[Mapping[str, Any]], mapping: Mapping[str, Any] | None
) -> None:
    if mapping is not None and mapping not in contexts:
        contexts.append(mapping)


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = _CAMEL_CASE_BOUNDARY.sub(" ", str(value))
    text = _SEPARATORS.sub(" ", text)
    return text.strip().lower()
