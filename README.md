# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler returns a title
update action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For matching events, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4999",
  "title": "Cursor researching: Existing issue title"
}
```

Non-status changes, status changes to any other status, missing issue metadata,
and titles already starting with `Cursor researching` return `None`.

## Local testing

```bash
python3 -m unittest -v
```
