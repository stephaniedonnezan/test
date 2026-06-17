# Linear issue title prefix automation

This repository contains a small handler that builds an issue-title update action
when a Linear issue status changes to `to research`.

```bash
python3 linear_title_prefix.py < event.json
```

For matching status-change payloads, the handler returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4960",
  "title": "Cursor researching: <original title>"
}
```
