# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Linear issue
status-change automation payloads.

When an issue status changes to `To Research`, `build_issue_title_update`
returns an action payload that prefixes the issue title with
`Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4579",
  "title": "Cursor researching: MB export corrections"
}
```

The handler returns `null` for other statuses, non-status updates, missing issue
metadata, or titles that already start with `Cursor researching`.

Run the tests with:

```bash
python3 -m unittest -v
```
