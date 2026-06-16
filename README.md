# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automation payloads. When an issue status changes to `to research`, the handler
returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-4933",
        "title": "Add a meter as example",
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4933",
  "title": "Cursor researching: Add a meter as example"
}
```

The handler ignores non-status changes, statuses other than `to research`, and
titles that already start with `Cursor researching`.
