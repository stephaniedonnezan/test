# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when a status-change payload
moves the issue to `To Research`.

The pure handler is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an `update_issue_title` action for matching
payloads and `None` otherwise.
