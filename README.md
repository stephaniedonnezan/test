# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status-change
event moves the issue into `to research`.

The main entry point is:

```python
from linear_title_prefix import build_issue_title_update
```

`build_issue_title_update(event)` returns an update action like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4434",
  "title": "Cursor researching: Sync work"
}
```

For non-matching events it returns `None`. The script can also read a JSON event
from stdin and print the update action when one is required.
