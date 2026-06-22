# Linear title prefix automation

This repository contains a small automation helper for Linear issue status
changes. When an issue moves to a status that normalizes to `to research`, the
helper returns an action that prefixes the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

For a matching status-change event, the command emits:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5087",
  "title": "Cursor researching: QA report - POI-5033"
}
```

Non-matching events produce no output.
