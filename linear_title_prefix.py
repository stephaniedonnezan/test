"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to to research.

    The automation payload can arrive either as a flat Linear trigger context or
    wrapped under keys such as ``triggerContext``/``data``/``issue``. This
    function keeps side effects out of the handler so the caller can perform the
    actual Linear update.
    """

    if not isinstance(event, Mapping):
        return None

    context = _issue_context(event)
    if not _is_status_change(context):
        return None

    status = _status_name(context)
    if _normalize(status) != _normalize(TARGET_STATUS):
        return None

    issue_id = _first_text(context, "id", "issueId", "issue_id", "identifier")
    title = _first_text(context, "title", "name")
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or _has_prefix(clean_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _issue_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge likely wrapper objects while letting outer trigger fields win."""

    context: dict[str, Any] = {}
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(_issue_context(value))
    context.update(event)
    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger = _first_text(context, "trigger", "action", "type")
    if trigger is not None and _normalize(trigger) in {
        "status changed",
        "status change",
        "state changed",
        "workflow state changed",
    }:
        return True

    webhook_type = _first_text(context, "webhookType", "webhook_type")
    if webhook_type is not None and _normalize(webhook_type) == "issue":
        updated_fields = context.get("updatedFields") or context.get("updated_fields")
        if _contains_status_field(updated_fields):
            return True

    return False


def _contains_status_field(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        return _normalize(updated_fields) in {"status", "state", "workflow state"}

    if isinstance(updated_fields, Sequence) and not isinstance(
        updated_fields, (str, bytes, bytearray)
    ):
        return any(_contains_status_field(field) for field in updated_fields)

    if isinstance(updated_fields, Mapping):
        return any(_contains_status_field(key) for key in updated_fields)

    return False


def _status_name(context: Mapping[str, Any]) -> str | None:
    direct_status = _first_text(context, "newStatus", "new_status", "status")
    if direct_status is not None:
        return direct_status

    for key in ("state", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            name = _first_text(value, "name")
            if name is not None:
                return name
        elif isinstance(value, str):
            return value

    return None


def _first_text(context: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str):
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None

    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    separated = re.sub(r"[_\-\s]+", " ", expanded)
    return separated.strip().casefold()
