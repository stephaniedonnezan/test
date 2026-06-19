# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes
to `to research`.

The main entry point is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an action payload such as:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3945",
  "title": "Cursor researching: Deleting a counter reading"
}
```

For non-matching events, already-prefixed titles, or incomplete payloads, it
returns `None`.

Run tests with:

```bash
python3 -m unittest -v
```
