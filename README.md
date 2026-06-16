# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation payloads.

When an issue changes status to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.
Payloads for other statuses or issues that already start with that prefix are
ignored.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4230",
  "title": "Cursor researching: Sustainability Declarations in Traceability"
}
```
