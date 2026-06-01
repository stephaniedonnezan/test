# Linear issue title prefix automation

This repository contains a small helper for Cursor automations that receive
Linear issue status-change payloads.

When an issue moves to `To Research`, `linear_title_prefix.py` builds an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run tests with:

```bash
python3 -m unittest -v
```
