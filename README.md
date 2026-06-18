# Linear research title prefix

This repository contains a small helper for Linear/Cursor automation payloads.
When an issue status-change event moves to `to research`, it returns an action
that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

Matching events return:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5063",
  "title": "Cursor researching: Improve performance"
}
```

Non-matching events return `None`.
