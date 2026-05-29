# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations.

When a Linear issue status-change event moves an issue to `To Research`, the
helper returns an `update_issue_title` action that prefixes the issue title with
`Cursor researching`.

The helper is intentionally side-effect free so the automation runner can decide
how to apply the returned action.
