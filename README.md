# Linear research title prefix automation

This repository contains a small helper for Linear/Cursor automation payloads.
When an issue status changes to `to research`, the helper builds a title update
that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "issueId": "POI-4965",
        "title": "performance: fetch the meter readings only once",
    }
)
```

The returned value is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4965",
  "title": "Cursor researching: performance: fetch the meter readings only once"
}
```

For any other status or non-status-change event, the helper returns `None`.

## CLI usage

The module can also read a JSON event from stdin and print the update action:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
