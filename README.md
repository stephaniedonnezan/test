# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automation payloads.

When a Linear issue status changes to `to research`, the helper returns an
action instructing the caller to prefix the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

`build_issue_title_update(event)` returns either:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-123",
  "title": "Cursor researching: Existing issue title"
}
```

or `None` when the event is not a status change to `to research`, the title is
already prefixed, or the payload is missing required issue data.
