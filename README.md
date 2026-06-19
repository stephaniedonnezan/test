# Linear research title prefix

This repository contains a small handler for Linear/Cursor automation payloads.
When an issue status changes to `to research`, `build_issue_title_update` returns
an action to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4765",
  "title": "Cursor researching: Original title"
}
```

Run tests with:

```bash
python3 -m unittest -v
```
