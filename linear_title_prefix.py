"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research".

    The automation trigger can provide issue details either as a flat payload or
    nested under keys like ``triggerContext``, ``data``, or ``issue``.
    """

    if not isinstance(event, Mapping):
        return None

    trigger_context = _mapping_value(event, "triggerContext", "trigger_context")
    data = _mapping_value(event, "data", "payload")
    issue = _first_mapping(
        _mapping_value(event, "issue"),
        _mapping_value(trigger_context, "issue") if trigger_context else None,
        _mapping_value(data, "issue") if data else None,
    )

    if not _is_status_change_event(event, trigger_context, data):
        return None

    new_status = _first_status_value(
        (trigger_context, event, data, issue),
        ("newStatus", "new_status", "status", "state", "workflowState", "workflow_state"),
    )
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text_value((issue, trigger_context, data, event), ("id", "issueId", "issue_id", "identifier"))
    title = _first_text_value((issue, trigger_context, data, event), ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or stripped_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _is_status_change_event(*contexts: Mapping[str, Any] | None) -> bool:
    for context in contexts:
        if not isinstance(context, Mapping):
            continue

        for key in ("trigger", "event", "action", "type", "webhookType", "webhook_type"):
            normalized = _normalize_words(context.get(key))
            if normalized in {"status changed", "status change"}:
                return True
            if normalized in {"issue updated", "updated issue"} and _updated_fields_include_status(context):
                return True

        if _updated_fields_include_status(context):
            return True

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    fields = _first_value(context, ("updatedFields", "updated_fields", "changedFields", "changed_fields"))
    if fields is None:
        return False

    if isinstance(fields, str):
        normalized_fields = {_normalize_words(fields)}
    elif isinstance(fields, Mapping):
        normalized_fields = {_normalize_words(key) for key in fields}
    elif isinstance(fields, Sequence) and not isinstance(fields, (bytes, bytearray)):
        normalized_fields = {_normalize_words(field) for field in fields}
    else:
        return False

    return bool(normalized_fields & {"status", "state", "workflow state", "workflowstatus"})


def _first_status_value(
    contexts: tuple[Mapping[str, Any] | None, ...],
    keys: tuple[str, ...],
) -> str | None:
    value = _first_value_from_contexts(contexts, keys)
    if isinstance(value, Mapping):
        value = _first_value(value, ("name", "title", "status"))
    return _coerce_text(value)


def _first_text_value(
    contexts: tuple[Mapping[str, Any] | None, ...],
    keys: tuple[str, ...],
) -> str | None:
    return _coerce_text(_first_value_from_contexts(contexts, keys))


def _first_value_from_contexts(
    contexts: tuple[Mapping[str, Any] | None, ...],
    keys: tuple[str, ...],
) -> Any:
    for context in contexts:
        if not isinstance(context, Mapping):
            continue
        value = _first_value(context, keys)
        if value is not None:
            return value
    return None


def _first_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _mapping_value(context: Mapping[str, Any] | None, *keys: str) -> Mapping[str, Any] | None:
    if not isinstance(context, Mapping):
        return None

    for key in keys:
        value = context.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _first_mapping(*values: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    for value in values:
        if isinstance(value, Mapping):
            return value
    return None


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _normalize_words(value: Any) -> str:
    text = _coerce_text(value)
    if text is None:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text.strip())
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()
