# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler returns an
action that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The script prints either an `update_issue_title` action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4898",
  "title": "Cursor researching: Duplicate meter reading found"
}
```

or `null` when the payload should not update the title.

## Tests

```bash
python3 -m unittest -v
```
