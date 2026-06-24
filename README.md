# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action to prefix
the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-4049",
        "title": "The audit tables randomly resize",
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4049",
  "title": "Cursor researching: The audit tables randomly resize"
}
```

The module can also be used as a CLI that reads the event JSON from stdin:

```sh
python3 linear_title_prefix.py < event.json
```
