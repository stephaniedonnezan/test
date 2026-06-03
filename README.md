# Linear research title prefix automation

Adds a `Cursor researching` title prefix when a Linear issue status-change event
moves the issue to `to research`.

The Python entrypoint is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an `update_issue_title` action for matching
payloads and `None` when no title change is needed.
