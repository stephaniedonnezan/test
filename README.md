# Linear issue title prefix automation

Builds a Linear issue title update action when an issue status changes to
`to research`.

Matching issues are prefixed with `Cursor researching`, for example:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4682",
  "title": "Cursor researching: Original issue title"
}
```

Run the tests with:

```bash
python3 -m unittest -v
```
