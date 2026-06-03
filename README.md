# Linear issue title automation

This repository contains a small handler for Cursor/Linear automation payloads.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an `update_issue_title` action that prefixes the issue title with
`Cursor researching`. Other status changes return no action, and titles that
already begin with `Cursor researching` are left unchanged.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The module can also be used as a CLI by passing a JSON payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```
