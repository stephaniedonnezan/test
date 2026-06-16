# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automation
payloads. When an issue changes status to `to research`, it builds an action to
prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching events, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4644",
  "title": "Cursor researching: Existing issue title"
}
```

The function returns `None` for non-status-change events, statuses other than
`to research`, missing issue details, or titles that already start with
`Cursor researching`.

Run tests with:

```bash
python3 -m unittest -v
```
