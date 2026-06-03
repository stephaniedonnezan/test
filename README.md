# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action that updates
the issue title to start with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The function returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4780",
  "title": "Cursor researching: Bug closing 2 deliveries"
}
```

For non-matching events, missing issue data, or titles already starting with the
prefix, it returns `None`.

Run tests with:

```bash
python3 -m unittest -v
```
