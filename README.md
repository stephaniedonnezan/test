# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations. When an
issue status-change payload indicates that the issue moved to `to research`,
`linear_title_prefix.py` returns an action instructing the caller to prefix the
issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(payload)
```

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4744",
  "title": "Cursor researching: Existing issue title"
}
```

No action is returned for other statuses, non-status updates, missing issue
details, or titles that already begin with `Cursor researching`.
