"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
STATUS_CHANGE_TOKENS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research".

    The automation payloads used by Linear can be flat or nested under
    ``triggerContext``, ``data.issue``, or ``issue``. This function keeps the
    parsing side-effect free so callers can decide how to submit the update.
    """

    if not isinstance(event, Mapping):
        return None

    context = _payload_context(event)
    if not _is_status_change(context):
        return None

    if _normalize_status(_status_value(context)) != RESEARCH_STATUS:
        return None

    issue_id = _string_value(_first_present(context, ("id", "issueId", "issue_id", "identifier")))
    title = _string_value(_first_present(context, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Linear automation payload locations into one mapping."""

    data = event.get("data")
    trigger_context = event.get("triggerContext")
    issue = event.get("issue")

    if isinstance(data, Mapping) and isinstance(data.get("issue"), Mapping):
        issue = data["issue"]

    context: dict[str, Any] = {}
    for source in (issue, data, trigger_context, event):
        if isinstance(source, Mapping):
            context.update(source)
    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    for field_name in ("trigger", "webhookType", "action", "type"):
        value = _string_value(context.get(field_name))
        if _normalize_token(value) in STATUS_CHANGE_TOKENS:
            return True

        if value is not None and _normalize_words(value) in {"issue updated", "updated issue"}:
            return _updated_fields_include_status(context.get("updatedFields"))

    return _updated_fields_include_status(context.get("updatedFields"))


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        candidates = re.split(r"[,;\s]+", updated_fields)
    elif isinstance(updated_fields, Mapping):
        candidates = updated_fields.keys()
    elif isinstance(updated_fields, (list, tuple, set, frozenset)):
        candidates = updated_fields
    else:
        return False

    return any(_normalize_token(_field_name(candidate)) in STATUS_FIELD_NAMES for candidate in candidates)


def _field_name(candidate: Any) -> str | None:
    if isinstance(candidate, str):
        return candidate
    if isinstance(candidate, Mapping):
        return _string_value(_first_present(candidate, ("name", "field", "key")))
    return None


def _status_value(context: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "status"):
        value = context.get(key)
        if value is not None:
            return value

    for key in ("state", "workflowState", "workflowStatus"):
        value = context.get(key)
        if isinstance(value, Mapping):
            nested_value = _first_present(value, ("name", "title", "status"))
            if nested_value is not None:
                return nested_value
        elif value is not None:
            return value

    return None


def _first_present(values: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = values.get(key)
        if value is not None:
            return value
    return None


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    text = _string_value(value)
    if text is None:
        return None
    return _normalize_words(text)


def _normalize_words(value: str) -> str:
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return " ".join(words.casefold().split())


def _normalize_token(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[^A-Za-z0-9]+", "", value).casefold()
