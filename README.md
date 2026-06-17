# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.

When an issue moves to `to research`, `build_issue_title_update(event)` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-123",
  "title": "Cursor researching: Existing issue title"
}
```

Events for other statuses, non-status updates, missing issue data, or titles that
already start with `Cursor researching` return `None`.
