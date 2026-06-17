# Linear issue title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when a status-change
event moves the issue to `To Research`.

The Python entrypoint is `linear_title_prefix.py`. It reads a JSON event from
stdin and prints either an `update_issue_title` action or `null`.
