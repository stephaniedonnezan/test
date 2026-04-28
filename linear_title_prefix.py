"""Build Linear issue title updates for Cursor research automation."""

from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status_changed"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    context = _mapping_at(event, "triggerContext") or event
    if _normalize_token(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize_phrase(status) != TARGET_STATUS:
        return None

    issue_id = _string_value(context.get("id", context.get("issueId")))
    title = _string_value(context.get("title"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _mapping_at(event: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = event.get(key)
    return value if isinstance(value, Mapping) else None


def _normalize_token(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""
    return "_".join(text.replace("-", "_").split()).lower()


def _normalize_phrase(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""
    return " ".join(text.replace("_", " ").replace("-", " ").split()).lower()


def _string_value(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""
