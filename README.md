# Linear issue title prefix helper

This repository contains a small, side-effect-free helper for Linear issue
status-change automations.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-123",
  "title": "Cursor researching: Existing issue title"
}
```

Events that are not status changes, do not target `to research`, are missing an
issue id or title, or already start with `Cursor researching` are ignored.
