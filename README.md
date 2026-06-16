# Linear research title prefix automation

This repository contains a small helper for Cursor/Linear automation events. When
a Linear issue status changes to `to research`, the helper builds an
`update_issue_title` action that prefixes the issue title with `Cursor
researching`.

```bash
python3 linear_title_prefix.py < event.json
```

The script prints either the title update action or `null`.
