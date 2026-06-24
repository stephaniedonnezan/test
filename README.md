# Linear issue title prefix automation

Adds a `Cursor researching` prefix to a Linear issue title when the issue status
changes to `to research`.

The handler accepts a Linear/Cursor webhook JSON payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

When the payload matches, it prints an `update_issue_title` action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-1234",
  "title": "Cursor researching: Existing issue title"
}
```
