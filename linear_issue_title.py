"""Compatibility exports for Linear issue title automation helpers."""

from linear_title_prefix import build_issue_title_update
from linear_title_prefix import derive_updated_title
from linear_title_prefix import handle_issue_status_changed
from linear_title_prefix import has_research_prefix
from linear_title_prefix import prefix_issue_title
from linear_title_prefix import update_issue_title_for_status
from linear_title_prefix import with_researching_prefix


__all__ = [
    "build_issue_title_update",
    "derive_updated_title",
    "handle_issue_status_changed",
    "has_research_prefix",
    "prefix_issue_title",
    "update_issue_title_for_status",
    "with_researching_prefix",
]
