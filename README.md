# Linear issue title prefix helper

This repository contains a small helper for Cursor/Linear automation payloads.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an action that updates the issue title to include the
`Cursor researching` prefix:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3551",
  "title": "Cursor researching: Front end implementation"
}
```

For other statuses or non-status-change events, the helper returns `None`.

Run the unit tests with:

```bash
python3 -m unittest -v
```
