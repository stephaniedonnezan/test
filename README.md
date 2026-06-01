# Linear research title automation

This repository contains a small handler for Linear issue status-change events.

When an issue status changes to `to research`, `linear_title_prefix.py` builds an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.
