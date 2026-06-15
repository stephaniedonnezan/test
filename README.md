# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue changes to `To Research`, the handler returns an action to prefix
the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4872",
  "title": "Cursor researching: Existing issue title"
}
```

Run tests with:

```bash
python3 -m unittest -v
```
