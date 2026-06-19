# Linear issue title automation

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves an issue to `to research`, the handler
returns an `update_issue_title` action that prefixes the title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

Matching events return:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5078",
  "title": "Cursor researching: Existing issue title"
}
```

Unrelated events, non-research statuses, missing titles, and titles already
starting with `Cursor researching` return `None`.
