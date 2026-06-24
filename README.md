# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automation events.
When a Linear issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The function returns `None` for non-status updates, statuses other than
`to research`, missing issue data, or titles that already start with
`Cursor researching`.

## CLI usage

Pass a JSON event on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

Matching events print the update action as JSON. Non-matching events produce no
output and exit successfully.

## Tests

```bash
python3 -m unittest -v
```
