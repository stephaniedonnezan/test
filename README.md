# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automation.

When an issue status changes to `to research`, `build_issue_title_update`
returns an `update_issue_title` action that prefixes the title with
`Cursor researching`.

```bash
python3 -m unittest -v
```
