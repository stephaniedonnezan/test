# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automations.

When an issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run the test suite with:

```bash
python3 -m unittest -v
```
