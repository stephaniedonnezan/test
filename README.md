# Linear title prefix automation

Adds `Cursor researching` to a Linear issue title when a status-change event moves
the issue to `To Research`.

The automation entry point is `linear_title_prefix.py`. It exposes
`build_issue_title_update(event)` for tests and can also read a JSON payload from
stdin:

```bash
python3 linear_title_prefix.py < event.json
```

Matching events emit an action payload:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5109",
  "title": "Cursor researching: Existing issue title"
}
```
