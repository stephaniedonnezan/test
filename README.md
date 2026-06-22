# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation payloads.

When an issue status changes to `to research`, `linear_title_prefix.py` emits an
`update_issue_title` action that prefixes the issue title with
`Cursor researching:`.
