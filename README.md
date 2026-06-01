# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when a status-change webhook
moves the issue to `to research`.

```bash
python3 linear_title_prefix.py < payload.json
```

The script prints an `update_issue_title` action with the prefixed title for
matching events, or no output when no title update is needed.
