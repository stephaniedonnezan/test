# Linear issue title research prefix

This repository contains a small handler for Linear/Cursor automation payloads.
When an issue status-change event moves an issue to `to research`, the handler
returns an `update_issue_title` action that prefixes the title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(payload)
```

The handler ignores non-status-change events, statuses other than
`to research`, missing issue data, and titles that already start with
`Cursor researching`.

You can also pipe a JSON payload to the module directly:

```sh
python3 linear_title_prefix.py < payload.json
```
