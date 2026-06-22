# Linear research title automation

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves to `to research`, the handler emits an
`update_issue_title` action that prefixes the title with `Cursor researching`.

The handler is intentionally idempotent: titles that already start with
`Cursor researching` are ignored.
