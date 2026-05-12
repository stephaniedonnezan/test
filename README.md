# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to the `to research` status, the handler returns an action
that updates the title to include the `Cursor researching` prefix.

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the CLI prints JSON in this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4160",
  "title": "Cursor researching: Implement non-conformities logging"
}
```
