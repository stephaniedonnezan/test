# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation events.

When a Linear issue status change moves an issue to `to research`,
`build_issue_title_update(event)` returns an action instructing the caller to
prefix the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4817",
  "title": "Cursor researching: Existing issue title"
}
```

The handler returns `null`/`None` for other statuses, non-status-change events,
missing issue metadata, or titles already beginning with `Cursor researching`.

Run tests with:

```bash
python3 -m unittest -v
```
