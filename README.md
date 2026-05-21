# Linear issue title prefix automation

This repository contains a small helper for Linear issue status-change
automations. When an issue moves to `to research`, the helper emits an action
that prefixes the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

The script prints an `update_issue_title` action for matching payloads and
prints nothing for non-matching payloads.
