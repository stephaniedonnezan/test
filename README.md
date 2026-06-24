# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automation.

When an issue status changes to `to research`, `build_issue_title_update(event)`
returns an action that prefixes the issue title with `Cursor researching`.
Already-prefixed titles are ignored.

Run the tests with:

```bash
python3 -m unittest -v
```
