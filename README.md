# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear issue status-change
events. When an issue moves to the `to research` status, the handler returns an
`update_issue_title` action that prefixes the title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the command prints JSON like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4914",
  "title": "Cursor researching: Existing title"
}
```

Non-status changes, non-research statuses, missing issue metadata, and titles
that already begin with `Cursor researching` produce no action.
