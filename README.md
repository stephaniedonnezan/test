# Linear issue title automation

Adds `Cursor researching` to a Linear issue title when the issue status changes
to `to research`.

The Python entry point is `linear_title_prefix.py`. It reads a Linear webhook or
Cursor automation payload from stdin and prints an `update_issue_title` action
when the title should be changed.
