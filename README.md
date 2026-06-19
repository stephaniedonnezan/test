# Linear issue title automation

This repository contains a small, side-effect-free handler for Linear issue
status-change events.

When an issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

The command prints no output when the event should not update the issue title.
