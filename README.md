# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `To Research`, the handler emits an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

For non-matching events, the handler prints nothing and exits successfully.
