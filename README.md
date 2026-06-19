# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.

When an issue status-change event moves an issue to `to research`, the handler
returns an `update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run tests with:

```bash
python3 -m unittest -v
```
