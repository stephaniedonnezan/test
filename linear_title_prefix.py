"""Build title update actions for Linear issue status-change events."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The automation trigger wraps Linear issue details in ``triggerContext``.
    This helper also accepts a flat context to keep tests and local invocation
    simple.
    """

    context = _trigger_context(event)
    if context is None:
        return None

    if _normalize(context.get("trigger")) != "status changed":
        return None

    if _normalize(_new_status(context)) != RESEARCH_STATUS:
        return None

    issue_id = _issue_id(context)
    title = _issue_title(context)
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _trigger_context(event: Any) -> Mapping[str, Any] | None:
    if not isinstance(event, Mapping):
        return None

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context

    return event


def _new_status(context: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "status"):
        status = context.get(key)
        if status:
            return status

    for key in ("newState", "state"):
        status = context.get(key)
        if isinstance(status, Mapping):
            return status.get("name")

    return None


def _issue_id(context: Mapping[str, Any]) -> str | None:
    issue_id = context.get("issueId") or context.get("id")
    if issue_id:
        return str(issue_id)

    issue = context.get("issue")
    if isinstance(issue, Mapping) and issue.get("id"):
        return str(issue["id"])

    return None


def _issue_title(context: Mapping[str, Any]) -> str | None:
    title = context.get("title")
    if isinstance(title, str):
        return title

    issue = context.get("issue")
    if isinstance(issue, Mapping) and isinstance(issue.get("title"), str):
        return issue["title"]

    return None


def _has_title_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    normalized = str(value).replace("_", " ").replace("-", " ").strip().casefold()
    return " ".join(normalized.split())
