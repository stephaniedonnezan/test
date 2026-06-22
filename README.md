# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

The handler prints the update action as JSON, or `null` when the event should not
change the issue title.
