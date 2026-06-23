# Linear research title prefix

This repository contains a small handler for Linear issue status-change events.

`build_issue_title_update(event)` returns an `update_issue_title` action that
prefixes an issue title with `Cursor researching: ` only when the issue status
changes to `to research`. Non-matching events return `None`.

The module can also be used as a CLI by piping a JSON event to
`linear_title_prefix.py`.
