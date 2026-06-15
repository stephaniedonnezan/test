# Linear research title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status-change
event moves the issue to `to research`.

The Python entrypoint is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an action payload like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4884",
  "title": "Cursor researching: lock qualified outputs"
}
```

For non-matching events, malformed payloads, or titles that already begin with
`Cursor researching`, the function returns `null`/`None`.

The module can also be run as a CLI that reads the event JSON from stdin:

```bash
python3 linear_title_prefix.py < event.json
```
