# Linear research title automation

This repository contains a small helper for Linear issue status-change
automations.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action requesting that the issue title be prefixed with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

Matching events produce:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3977",
  "title": "Cursor researching: Write backend tests"
}
```
