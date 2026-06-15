# Linear issue title automation

This repository contains a small handler for Linear issue status-change events.

When an issue status changes to `to research`, `build_issue_title_update` returns
an `update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```
