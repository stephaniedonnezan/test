"""Build title updates for Linear issues entering research."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: "
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The Cursor automation payload may include the Linear issue fields at the
    top level, under ``triggerContext``, or under a webhook-style ``data.issue``.
    """

    if not isinstance(event, Mapping):
        return None

    context = _combined_context(event)
    if not _is_status_change(context):
        return None

    if _normalize_status(_first_present(context, "newStatus", "new_status", "status")) != TARGET_STATUS:
        state = _as_mapping(context.get("state"))
        workflow_state = _as_mapping(context.get("workflowState"))
        if _normalize_status(_first_present(state, "name")) != TARGET_STATUS and _normalize_status(
            _first_present(workflow_state, "name")
        ) != TARGET_STATUS:
            return None

    issue_id = _string_value(_first_present(context, "id", "issueId", "issue_id", "identifier"))
    title = _string_value(_first_present(context, "title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIXED_TITLE}{title}",
    }


def _combined_context(event: Mapping[str, Any]) -> dict[str, Any]:
    trigger_context = _as_mapping(event.get("triggerContext"))
    data = _as_mapping(event.get("data"))
    issue = _as_mapping(event.get("issue")) or _as_mapping(data.get("issue"))

    combined: dict[str, Any] = {}
    for source in (issue, data, trigger_context, event):
        combined.update(source)
    return combined


def _is_status_change(context: Mapping[str, Any]) -> bool:
    direct_fields = ("trigger", "action", "type")
    direct_values = [_normalize_status(_first_present(context, field)) for field in direct_fields]
    webhook_type = _normalize_status(_first_present(context, "webhookType"))

    if any(value == "status changed" for value in direct_values):
        return True

    if webhook_type == "status changed":
        return True

    if any(value in {"issue updated", "updated issue"} for value in direct_values + [webhook_type]):
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if isinstance(updated_fields, str):
        return _normalize_status(updated_fields) in {"status", "state", "workflow state"}

    if isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, (list, tuple, set, frozenset)):
        fields = updated_fields
    else:
        return False

    return any(_normalize_status(field) in {"status", "state", "workflow state"} for field in fields)


def _first_present(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _normalize_status(value: Any) -> str | None:
    text = _string_value(value)
    if not text:
        return None

    with_camel_spacing = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    words = re.sub(r"[^A-Za-z0-9]+", " ", with_camel_spacing).strip().lower()
    return re.sub(r"\s+", " ", words)


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value).strip() or None


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
