# Linear research title prefix

This repository contains a small handler for Linear status-change automations.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue moves to `to research`, prefixing the issue title with
`Cursor researching`.
