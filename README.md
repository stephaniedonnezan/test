# Linear issue title automation

This repository contains a small helper for Cursor/Linear issue webhooks.

`build_issue_title_update(event)` returns an `update_issue_title` action when an
issue status-change payload moves to `to research`. The generated title is
prefixed with `Cursor researching` unless that prefix is already present.
