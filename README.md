# Linear research title prefix automation

This repository contains a small helper for Linear issue automations. When a
status-change event moves an issue to `to research`, the helper returns an
action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4644",
  "title": "Cursor researching: Existing issue title"
}
```
