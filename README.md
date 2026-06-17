# Linear research title prefix

This repository contains a small payload processor for Cursor/Linear automation.

When a Linear issue status changes to `to research`, `linear_title_prefix.py`
builds an `update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching event, the script prints JSON similar to:

```json
{"action": "update_issue_title", "issueId": "POI-4988", "title": "Cursor researching: Original title"}
```

The handler ignores non-status events, statuses other than `to research`, and
titles that already start with `Cursor researching`.
