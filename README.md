# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automation.

When an issue status changes to `to research`, `build_issue_title_update` returns
an update action that prefixes the issue title with `Cursor researching`.
Existing prefixed titles are ignored to avoid duplicate prefixes.

Run tests with:

```bash
python3 -m unittest -v
```
