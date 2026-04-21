"""Helpers for Linear issue title updates on status changes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


RESEARCH_STATUS = "to research"
RESEARCH_PREFIX = "Cursor researching: "


def _normalize(value: Any) -> str:
    """Return a normalized lowercase string for comparisons."""
    if value is None:
        return ""
    return str(value).strip().lower()


def add_research_prefix_on_status_change(payload: dict[str, Any]) -> dict[str, Any]:
    """Add `Cursor researching` to title when status changes to `to research`.

    The function returns a copied payload and never mutates the input.
    If the title already starts with the prefix (case-insensitive), it is left
    unchanged to avoid duplicates.
    """

    updated = deepcopy(payload)
    new_status = _normalize(updated.get("newStatus"))
    title = str(updated.get("title", "")).strip()

    if new_status == RESEARCH_STATUS and title:
        if not _normalize(title).startswith(_normalize(RESEARCH_PREFIX)):
            updated["title"] = f"{RESEARCH_PREFIX}{title}"

    return updated
