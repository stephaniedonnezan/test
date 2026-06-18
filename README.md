# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear issue status-change
events. When an issue moves to `To Research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

The core function is `build_issue_title_update` in `linear_title_prefix.py`.
