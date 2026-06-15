# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue status changes to `To Research`, the handler returns an action to
prefix the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

The script prints either:

- an `update_issue_title` action with the issue ID and prefixed title
- `null` when the payload does not represent a status change to `To Research`
