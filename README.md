# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status change moves a Linear issue to `to research`, the handler
returns an `update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

The process exits with status 0 and prints JSON when a title update is needed.
It exits with status 1 when the event should be ignored.
