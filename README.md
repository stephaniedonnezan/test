# Linear issue title research prefix

This repository contains a small helper for Cursor/Linear automations.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status changes to `to research`, prefixing the title with
`Cursor researching`.
