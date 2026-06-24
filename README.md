# Linear research title prefix automation

This repository contains a small handler for Linear status-change automations.

When an issue status change moves an issue to `to research`, the handler returns
an `update_issue_title` action that prefixes the issue title with
`Cursor researching:`.

```bash
python3 linear_title_prefix.py < event.json
```
