# Linear research title prefix

This repository contains a small handler for Linear status-change automation.

When an issue status changes to `to research`, `linear_title_prefix.py` returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.
