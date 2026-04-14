"""Compatibility helpers for Linear issue title updates."""

from __future__ import annotations

from linear_title_prefix import (
    RESEARCH_STATUS_NAME as TO_RESEARCH_STATUS,
)
from linear_title_prefix import (
    RESEARCH_TITLE_PREFIX as RESEARCH_PREFIX,
)
from linear_title_prefix import derive_updated_title
from linear_title_prefix import maybe_update_issue_title
from linear_title_prefix import update_issue_title_for_status


def updated_title_for_status_change(payload):
    """Compatibility alias retained for previous automation naming."""
    return derive_updated_title(payload)


def update_issue_title_from_event(event):
    """Compatibility alias retained for previous automation naming."""
    return derive_updated_title(event)
