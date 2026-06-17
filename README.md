# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status changes to `to research`, `linear_title_prefix.py` builds an
action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The helper returns `None` for unrelated triggers, statuses other than
`to research`, missing issue metadata, or titles that already start with
`Cursor researching`.

Run the unit tests with:

```bash
python3 -m unittest -v
```
