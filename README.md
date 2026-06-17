# Linear title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when an issue status
changes to `To Research`.

The main entry point is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an `update_issue_title` action when the
payload qualifies, or `None` when no title change is needed.
