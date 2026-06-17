# Linear research title prefix

This repository contains a small handler for Cursor/Linear automations.  When a
Linear issue status changes to `to research`, the handler builds an action to
prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching payload, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4970",
  "title": "Cursor researching: Existing issue title"
}
```

The function returns `None` when the event is not a status-change transition to
`to research`, the title already starts with `Cursor researching`, or the issue
id/title cannot be determined.

The module also supports a simple stdin JSON CLI:

```bash
python3 linear_title_prefix.py < event.json
```

Run tests with:

```bash
python3 -m unittest -v
```
