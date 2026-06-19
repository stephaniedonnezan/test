# Linear title prefix automation

Adds a `Cursor researching` title prefix when a Linear issue changes status to
`to research`.

The Python entrypoint is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an `update_issue_title` action for matching
status-change events and `None` for all other webhook payloads.
