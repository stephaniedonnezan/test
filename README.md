# Linear issue title prefix automation

Builds a Linear issue title update when a Cursor/Linear status-change event moves an
issue into `to research`.

## Behavior

`build_issue_title_update(event)` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4826",
  "title": "Cursor researching: Existing title"
}
```

The helper returns `None` for other status changes, non-status updates, missing issue
metadata, or titles that already start with `Cursor researching`.

## CLI

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
