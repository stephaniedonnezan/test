# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation events. When an issue moves to `To Research`, the handler returns an
action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4757",
  "title": "Cursor researching: Original title"
}
```

Run tests with:

```bash
python3 -m unittest -v
```
