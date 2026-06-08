"""Compatibility exports for Linear issue-title prefix helpers."""

from linear_title_prefix import (
    TARGET_STATUS as TO_RESEARCH_STATUS,
    TITLE_PREFIX as RESEARCHING_PREFIX,
    build_issue_title_update,
    derive_updated_title,
    handle_issue_status_changed,
    updated_title_for_status_change,
    update_issue_title_for_status,
    with_researching_prefix,
)

__all__ = [
    "RESEARCHING_PREFIX",
    "TO_RESEARCH_STATUS",
    "build_issue_title_update",
    "derive_updated_title",
    "handle_issue_status_changed",
    "updated_title_for_status_change",
    "update_issue_title_for_status",
    "with_researching_prefix",
]
