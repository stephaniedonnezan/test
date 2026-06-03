# Linear research title prefix automation

Adds a `Cursor researching` prefix to a Linear issue title when the issue status
changes to `to research`.

The main entry point is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an action payload like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4803",
  "title": "Cursor researching: Existing issue title"
}
```

For non-matching events, or titles that already start with `Cursor researching`,
the function returns `None`.

You can also pipe a JSON event into the script:

```bash
python3 linear_title_prefix.py < event.json
```
