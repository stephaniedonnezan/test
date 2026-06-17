# Linear issue title prefix automation

Builds an issue title update when a Linear issue status changes to `To Research`.

```bash
python3 linear_title_prefix.py < payload.json
```

For matching status-change events, the handler returns an `update_issue_title`
action that prefixes the issue title with `Cursor researching`.
