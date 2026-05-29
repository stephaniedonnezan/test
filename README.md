# Linear issue title prefix automation

Builds an issue title update when a Linear issue status changes to `to research`.

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching status-change event, the transformer emits an update action with the
issue title prefixed by `Cursor researching`.
