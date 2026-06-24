# Linear research title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status changes to `to research`, `linear_title_prefix.py` builds an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run the test suite with:

```bash
python3 -m unittest -v
```
