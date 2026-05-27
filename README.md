# Linear issue title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when an issue status
changes to `to research`.

The main entry point is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an action dictionary for matching events and
`None` when no title update is needed.
