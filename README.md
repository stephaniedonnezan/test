# Linear issue title prefix automation

This repository contains a small helper for Cursor automations that react to
Linear issue status changes. When an issue status changes to `to research`, the
helper returns an action payload to prefix the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The helper returns `None` for unrelated statuses, unrelated event types, missing
issue metadata, or titles that already start with `Cursor researching`.

## Verification

```bash
python3 -m unittest -v
```
