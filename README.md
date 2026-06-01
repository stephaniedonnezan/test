# Linear research title prefix automation

This repository contains a small handler for Linear status-change automations.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.
Other status changes are ignored, and titles that already begin with
`Cursor researching` are not updated again.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The module can also read a JSON payload from stdin and print the requested
update action:

```sh
python3 linear_title_prefix.py < payload.json
```
