"""Compatibility exports for Linear issue title automation."""

from linear_title_prefix import (
    TITLE_PREFIX,
    build_issue_title_update,
    handle_issue_status_changed,
    handleIssueStatusChanged,
)

__all__ = [
    "TITLE_PREFIX",
    "build_issue_title_update",
    "handle_issue_status_changed",
    "handleIssueStatusChanged",
]
