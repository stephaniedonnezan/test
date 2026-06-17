# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automation events.
When a Linear issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

For example, a status-change payload for issue `POI-3133` with title
`Needs research` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3133",
  "title": "Cursor researching: Needs research"
}
```

Run tests with:

```bash
python3 -m unittest -v
```
