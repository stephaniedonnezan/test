# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.

When an issue moves to `To Research`, `linear_title_prefix.py` returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```
