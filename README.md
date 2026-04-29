# Linear issue title prefix automation

This automation builds a Linear issue title update when an issue status-change
event moves to `to research`.

Use `build_issue_title_update(event)` from `linear_title_prefix.py`. Matching
events return an `update_issue_title` action with the title prefixed by
`Cursor researching: `; non-matching events return `None`.
