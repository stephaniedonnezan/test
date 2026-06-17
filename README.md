# Linear research title prefix

This repository contains a small automation helper for Linear issue events.

When an issue status-change event moves an issue to `to research`, the helper
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5013",
  "title": "Cursor researching: Loading message goes behind Mass Balance items"
}
```

The helper ignores non-status changes, statuses other than `to research`, and
titles that already start with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
