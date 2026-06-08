"""Compatibility wrapper for Linear issue research title helpers."""

from linear_issue_title import build_issue_title_update
from linear_issue_title import derive_updated_title
from linear_issue_title import main
from linear_issue_title import prefix_research_title
from linear_issue_title import update_issue_title_for_status

__all__ = [
    "build_issue_title_update",
    "derive_updated_title",
    "main",
    "prefix_research_title",
    "update_issue_title_for_status",
]


if __name__ == "__main__":
    raise SystemExit(main())
