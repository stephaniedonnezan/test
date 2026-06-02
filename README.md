# Linear research status title prefix

This repository contains a small handler for Linear issue status-change
automation payloads. When an issue changes status to `to research`, the handler
returns an action to prefix the issue title with `Cursor researching`.

The handler accepts flat automation trigger payloads and common nested Linear
webhook payloads:

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching event, `action` is shaped like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4480",
  "title": "Cursor researching: GET /energy-allocation failed"
}
```

Non-status-change events, status changes to anything other than `to research`,
and titles that already start with `Cursor researching` are ignored or left
unprefixed.

## Running tests

```bash
python3 -m unittest -v
```
