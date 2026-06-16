# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves a Linear issue to `to research`, the
handler returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching events, the action shape is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4938",
  "title": "Cursor researching: Existing issue title"
}
```

The handler ignores non-status changes, status changes to any other status, and
titles that already begin with `Cursor researching`.

## CLI usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
