# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automations.

When an issue status changes to `to research`, `linear_title_prefix.py` returns
an `update_issue_title` action that prefixes the issue title with
`Cursor researching`. Other statuses and non-status-change events produce no
action.
