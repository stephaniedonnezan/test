# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status-change payload moves an issue to `to research`, the helper
returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5074",
  "title": "Cursor researching: Original title"
}
```

The helper ignores non-status triggers, statuses other than `to research`, and
titles that already begin with `Cursor researching`.

To run it as a CLI, pass a JSON payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```bash
python3 -m unittest -v
```
