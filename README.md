# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automations. When a
Linear issue status change moves an issue to `to research`, the handler returns
an action to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5090",
  "title": "Cursor researching: Add Input"
}
```

The handler ignores non-status updates, statuses other than `to research`,
missing issue data, and titles that already start with `Cursor researching`.

Run the test suite with:

```bash
python3 -m unittest -v
```
