# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status-change event moves an issue to `to research`, the helper
returns an action that prefixes the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4964",
  "title": "Cursor researching: Invite link not showing after user is invited"
}
```

Events that are not status changes, do not move to `to research`, are missing an
issue identifier or title, or already start with `Cursor researching` are ignored.

## Usage

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The module can also be used as a JSON stdin/stdout command:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
