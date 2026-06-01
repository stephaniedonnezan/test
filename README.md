# Linear research title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when an issue status
changes to `to research`.

The handler returns an `update_issue_title` action for matching webhook payloads:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4500",
  "title": "Cursor researching: Implement Certifhy chip in audit"
}
```

Run tests with:

```sh
python3 -m unittest -v
```
