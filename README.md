# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automation payloads.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action describing the title update that should be applied:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4965",
  "title": "Cursor researching: existing title"
}
```

Non-status changes, moves to other statuses, and titles that already start with
`Cursor researching` are ignored or left unchanged.
