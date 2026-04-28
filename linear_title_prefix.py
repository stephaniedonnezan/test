"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import re
from typing import Any, Mapping


PREFIX = "Cursor researching"
PREFIXED_TITLE_RE = re.compile(r"^\s*cursor\s+researching\b", re.IGNORECASE)


def _normalize(value: Any) -> str:
    """Normalize webhook strings that may vary by case or separators."""
    if value is None:
        return ""

    return re.sub(r"[\s_-]+", " ", str(value).strip().casefold())


def _context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context

    return event


def _string_value(context: Mapping[str, Any], key: str) -> str:
    value = context.get(key)
    if value is None:
        return ""

    return str(value).strip()


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters to research.

    The automation runtime sends Linear metadata under ``triggerContext``, but
    tests and local callers may pass the same fields at the top level.
    """
    if not isinstance(event, Mapping):
        return None

    context = _context(event)
    if _normalize(context.get("trigger")) != "status changed":
        return None

    target_status = context.get("newStatus", context.get("status"))
    if _normalize(target_status) != "to research":
        return None

    issue_id = _string_value(context, "id")
    title = _string_value(context, "title")
    if not issue_id or not title:
        return None

    if PREFIXED_TITLE_RE.match(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }
