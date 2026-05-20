# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation events.
When an issue status-change event moves to `To Research`, the handler returns an
action to update the issue title with the `Cursor researching` prefix.

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the command prints:

```json
{"action": "update_issue_title", "issueId": "POI-4679", "title": "Cursor researching: Existing title"}
```

Non-matching events produce no output.
