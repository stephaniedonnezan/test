# Linear research title prefix

This repository contains a small, side-effect free handler for Cursor Linear
automation payloads. When a Linear issue status-change event moves an issue to
`to research`, the handler returns an action that prefixes the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching payload, `action` is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4998",
  "title": "Cursor researching: Why are there four types of events?"
}
```

The handler ignores non-status changes, statuses other than `to research`, and
titles that already start with `Cursor researching`.

## CLI

The module can also read a JSON event from stdin and print the action or `null`:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
