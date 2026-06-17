# Linear research title prefix automation

This repository contains a small helper for Linear issue status-change
automations. When an issue status changes to `to research`, the helper builds an
issue-title update action that prefixes the existing title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update({
    "trigger": "status_changed",
    "newStatus": "To Research",
    "id": "POI-4965",
    "title": "performance: fetch meter readings once",
})
```

The returned value is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4965",
  "title": "Cursor researching: performance: fetch meter readings once"
}
```

For non-status changes, statuses other than `to research`, missing issue data,
or titles that already begin with `Cursor researching`, the helper avoids
creating duplicate or unrelated updates.

## Test

```bash
python3 -m unittest -v
```
