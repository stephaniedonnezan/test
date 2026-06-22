# Linear research title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status-change
event moves the issue into `to research`.

The core helper is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an action dictionary like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4885",
  "title": "Cursor researching: unlock qualified outputs"
}
```

Events that are not status changes, do not target `to research`, have missing
issue metadata, or already start with `Cursor researching` return `None`.

## CLI smoke test

```bash
echo '{"trigger":"status_changed","newStatus":"to research","id":"POI-4885","title":"unlock qualified outputs"}' \
  | python3 linear_title_prefix.py
```

## Tests

```bash
python3 -m unittest -v
```
