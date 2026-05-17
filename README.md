# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when a status-change event
moves the issue to `to research`.

The main entry point is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an `update_issue_title` action for matching
events and `None` for events that should be ignored.
