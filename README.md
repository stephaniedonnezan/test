# Linear issue title prefix automation

This repository contains a small helper for Linear issue status-change
automations. When an issue moves to the `to research` status, the helper builds
an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "To Research",
        "id": "POI-4960",
        "title": "User & permission management (Org Admin)",
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4960",
  "title": "Cursor researching: User & permission management (Org Admin)"
}
```

Events that are not status changes, do not move to `to research`, are missing an
issue id/title, or already start with `Cursor researching` are ignored.

Run the tests with:

```bash
python3 -m unittest -v
```
