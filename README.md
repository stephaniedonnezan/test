# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Linear issue
status-change events. When an issue status changes to `to research`, the handler
returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-4033",
        "title": "Adjust code for float operation issues",
    }
)
```

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4033",
  "title": "Cursor researching: Adjust code for float operation issues"
}
```

For non-status changes, statuses other than `to research`, or titles that already
begin with `Cursor researching`, the handler returns `None`.

Run the tests with:

```sh
python3 -m unittest -v
```
