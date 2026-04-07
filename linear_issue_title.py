"""Compatibility helpers for Linear issue-title updates."""

from __future__ import annotations

from typing import Any

from linear_title_prefix import RESEARCH_TITLE_PREFIX
from linear_title_prefix import derive_updated_title

RESEARCHING_MARKER = RESEARCH_TITLE_PREFIX


def maybe_update_issue_title(payload: dict[str, Any], marker: str = RESEARCHING_MARKER) -> str | None:
    """Return updated title when status is set to `to research`."""
    del marker  # Marker is fixed to the product requirement for consistency.
    return derive_updated_title(payload)
