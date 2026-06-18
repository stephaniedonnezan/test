# Linear title prefix automation

Adds a `Cursor researching` prefix to a Linear issue title when a status-change event
moves the issue to `To Research`.

The Python entrypoint is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an update action when the event should change
the issue title, or `None` when no title update is needed.
