# Linear issue title prefix automation

This repository contains a small handler for Linear status-change events.

`build_issue_title_update(event)` returns an `update_issue_title` action that
prefixes the issue title with `Cursor researching` when the issue moves to
`to research`. It ignores unrelated events and titles that already start with
the prefix.
