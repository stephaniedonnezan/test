# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status-change event moves an issue to `to research`, the
handler returns an action to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching payload, `action` has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4730",
  "title": "Cursor researching: Existing issue title"
}
```

Non-status-change events, non-research statuses, missing issue data, and titles
that already start with `Cursor researching` return `None`.

Run tests with:

```sh
python3 -m unittest -v
```
