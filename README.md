# Linear issue title prefix automation

This automation helper builds a Linear issue-title update when an issue status
changes to `to research`.

For matching issue status-change events, `build_issue_title_update(event)`
returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4728",
  "title": "Cursor researching: Existing issue title"
}
```

Non-matching events return `None`. The module can also be used as a small CLI
that reads a JSON event from stdin and prints the update action when one is
needed.
