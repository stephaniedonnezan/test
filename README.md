# Linear issue title prefix automation

Adds a small handler for Linear status-change events. When an issue status
changes to `to research`, the handler returns an action that prefixes the issue
title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-4930",
        "title": "Optimize offtaker fifo allocation",
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4930",
  "title": "Cursor researching: Optimize offtaker fifo allocation"
}
```

The handler ignores unrelated events, status changes to any other status, and
titles that already start with `Cursor researching`.

## CLI

The module can also read a JSON event from standard input:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
