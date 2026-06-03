# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler builds an action that prefixes
the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching event, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4811",
  "title": "Cursor researching: Create production site form"
}
```

For non-status-change events, statuses other than `to research`, missing issue
data, or titles that already start with `Cursor researching`, it returns `None`.

The module can also be used as a stdin JSON CLI:

```bash
python3 linear_title_prefix.py < event.json
```

Run the tests with:

```bash
python3 -m unittest -v
```
