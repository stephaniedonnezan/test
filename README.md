# Linear issue title research prefix

This project builds an issue title update action when a Linear issue status
changes to `To Research`.

When the trigger is a status change and the new status normalizes to
`to research`, `linear_title_prefix.py` returns an action that prefixes the
issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

The handler skips non-status changes, other statuses, missing issue metadata,
and titles that already start with `Cursor researching`.
