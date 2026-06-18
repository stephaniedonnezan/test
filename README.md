# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation payloads.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.
Titles that already start with that prefix are ignored so repeated webhook
deliveries do not duplicate it.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5043",
  "title": "Cursor researching: Original issue title"
}
```

You can also pipe a JSON event to the module directly:

```sh
python3 linear_title_prefix.py < event.json
```

Run tests with:

```sh
python3 -m unittest -v
```
