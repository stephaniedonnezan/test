# Linear issue title prefix automation

This automation builds a Linear issue title update when an issue status-change
event moves to `To Research`.

When the condition matches, the handler returns:

```json
{
  "action": "update_issue_title",
  "issueId": "<issue id>",
  "title": "Cursor researching: <current title>"
}
```

The handler no-ops for non-status updates, other target statuses, missing issue
metadata, and titles that already start with `Cursor researching`.
