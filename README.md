# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, it returns an action to prefix the issue
title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

For a matching event, the script prints:

```json
{"action": "update_issue_title", "issueId": "POI-3936", "title": "Cursor researching: Show Production Site Mass Balance"}
```

The handler is idempotent and skips titles that already begin with
`Cursor researching`.
