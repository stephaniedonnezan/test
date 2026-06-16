# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status-change event moves an issue to `To Research`, the helper
builds an action to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching event, `action` has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4906",
  "title": "Cursor researching: Original issue title"
}
```

Non-matching events return `None`, including status changes to other statuses
and issues whose titles already start with `Cursor researching`.

The module can also be used as a CLI that reads a JSON event from stdin:

```sh
python3 linear_title_prefix.py < event.json
```
