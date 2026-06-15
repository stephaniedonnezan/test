# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue status changes to `to research`, the handler builds an update
action that prefixes the issue title with `Cursor researching`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching event, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4013",
  "title": "Cursor researching: Original title"
}
```

For non-matching events, invalid payloads, or titles that already start with
`Cursor researching`, it returns `None`.

The module also supports stdin JSON:

```bash
python3 linear_title_prefix.py < event.json
```

## Test

```bash
python3 -m unittest -v
```
