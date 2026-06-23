# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Linear/Cursor
automation payloads.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an `update_issue_title` action that prefixes the issue title with
`Cursor researching`. Other status changes return `null`/`None`.

```bash
python3 linear_title_prefix.py < payload.json
python3 -m unittest -v
```
