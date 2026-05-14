# Linear research title automation

This repository contains a small handler for Linear issue automation payloads.

When an issue status changes to `to research`, `build_issue_title_update` returns
an action that prefixes the issue title with `Cursor researching`:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-4139",
        "title": "Error: can not calculate average on an empty array",
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4139",
  "title": "Cursor researching: Error: can not calculate average on an empty array"
}
```

The handler ignores non-status changes, statuses other than `to research`, and
titles that already start with `Cursor researching`.

## CLI

The module can also read a JSON event from stdin and print the update action:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
