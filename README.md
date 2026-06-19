# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action that prefixes
the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching event, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3611",
  "title": "Cursor researching: Add a Container Delivery Emission Strategy handler Strategy"
}
```

Non-status changes, other target statuses, missing issue data, and titles that
already start with `Cursor researching` return `None`.

## CLI

The module also accepts a JSON event on stdin:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
