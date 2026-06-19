# Linear research title prefix

This repository contains a small handler for Linear issue automation payloads.
When an issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-4051",
        "title": "Fix frontend font fallback",
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4051",
  "title": "Cursor researching: Fix frontend font fallback"
}
```

Existing titles that already begin with `Cursor researching` are ignored so the
prefix is not duplicated.

## CLI

The module can also read a JSON event from stdin and print the action:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
