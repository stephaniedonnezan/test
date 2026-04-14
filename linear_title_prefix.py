"""Utilities to prefix Linear issue titles for research status changes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

RESEARCH_STATUS = "to research"
RESEARCH_TITLE_PREFIX = "Cursor researching"


def _normalize_status(status: str | None) -> str:
    """Normalize status values for case-insensitive comparisons."""
    return (status or "").strip().casefold()


def _is_research_status(status: str | None) -> bool:
    """Return True when the given status is equivalent to 'to research'."""
    return _normalize_status(status) == RESEARCH_STATUS


def _has_prefix(title: str, prefix: str = RESEARCH_TITLE_PREFIX) -> bool:
    """Check if a title already starts with the configured prefix."""
    return title.strip().startswith(prefix)


def update_title_for_status(
    title: str,
    new_status: str | None,
    prefix: str = RESEARCH_TITLE_PREFIX,
) -> str:
    """
    Prefix titles when the issue transitions to the research status.

    Example:
        update_title_for_status("Extract data log", "to research")
        -> "Cursor researching - Extract data log"
    """
    if not title:
        return prefix if _is_research_status(new_status) else title

    if _is_research_status(new_status) and not _has_prefix(title, prefix):
        return f"{prefix} - {title}"

    return title


def apply_research_title_prefix(event: dict[str, Any]) -> dict[str, Any]:
    """
    Return a copied event payload with the research title prefix applied.

    Expects a payload shape similar to:
      {
        "triggerContext": {
          "newStatus": "to research",
          "title": "Issue title"
        }
      }
    """
    updated = deepcopy(event)
    context = updated.get("triggerContext", {})
    if not isinstance(context, dict):
        return updated

    title = context.get("title")
    if isinstance(title, str):
        context["title"] = update_title_for_status(title, context.get("newStatus"))
    return updated
