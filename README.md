# Linear research title prefix automation

This repository contains a small handler for Linear/Cursor automation payloads.
When an issue status-change event moves to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with `Cursor
researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(payload)
```

The function returns `None` for non-status updates, other statuses, missing issue
metadata, or titles that do not need an update. It avoids adding the prefix more
than once.

## CLI

The module can also read a JSON payload from stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

When an update is needed, the CLI prints the action as JSON.

## Tests

```bash
python3 -m unittest -v
```
