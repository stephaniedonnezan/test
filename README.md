# Linear title prefix automation

This repository contains a small helper for Linear issue status-change
automations.

When an issue status changes to `to research`, `linear_title_prefix.py` builds an
`update_issue_title` action that prefixes the issue title with
`Cursor researching:`.

```bash
python3 linear_title_prefix.py < event.json
```

Run the tests with:

```bash
python3 -m unittest -v
```
