# Linear issue title prefix automation

Adds a `Cursor researching` prefix to a Linear issue title when a status-change
event moves the issue to `to research`.

The main entry point is:

```python
from linear_title_prefix import build_issue_title_update
```

`build_issue_title_update(event)` returns an action for the automation runner:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4676",
  "title": "Cursor researching: Existing issue title"
}
```

It returns `None` for unrelated triggers, non-research statuses, missing issue
metadata, or titles that already start with `Cursor researching`.
