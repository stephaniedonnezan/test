# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Linear issue
status-change automation.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action instructing the caller to prefix the issue title with
`Cursor researching`.

```bash
python3 -m unittest -v
```
