"""Build Linear issue-title updates for research status transitions."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The automation trigger can provide either a flat payload or nested Linear
    webhook data. This helper keeps the side-effect-free decision in one place:
    only issue status-change events whose new status normalizes to
    ``to research`` get a non-duplicated ``Cursor researching`` title prefix.
    """

    if not isinstance(event, Mapping):
        return None

    context = _issue_context(event)
    if not _is_status_change_event(context):
        return None
    if _normalize_status(_first_present(context, ("newStatus", "new_status", "status"))) != TARGET_STATUS:
        state = context.get("state")
        if not isinstance(state, Mapping) or _normalize_status(state.get("name")) != TARGET_STATUS:
            return None

    issue_id = _string_or_none(_first_present(context, ("id", "issueId", "issue_id", "identifier")))
    title = _string_or_none(context.get("title"))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _issue_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge supported payload locations with top-level values taking priority."""

    context: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(issue)
        context.update(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        context.update(issue)

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = (
        context.get("trigger"),
        context.get("triggerType"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    )

    for trigger_value in trigger_values:
        normalized_trigger = _normalize_status(trigger_value)
        compact_trigger = normalized_trigger.replace(" ", "")

        if compact_trigger in {"statuschanged", "statuschange"}:
            return True

        if normalized_trigger in {"issue updated", "updated issue"}:
            updated_fields = context.get("updatedFields")
            if isinstance(updated_fields, str):
                return _normalize_status(updated_fields) in {"status", "state"}
            if isinstance(updated_fields, (list, tuple, set)):
                return any(
                    _normalize_status(field) in {"status", "state"}
                    for field in updated_fields
                )

    return False


def _normalize_status(value: Any) -> str:
    text = _string_or_none(value)
    if text is None:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _first_present(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None
