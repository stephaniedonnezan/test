# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear issue automation payloads.

When an issue status-change event moves a Linear issue to `to research`, the handler
returns an action that prefixes the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4914",
  "title": "Cursor researching: Existing issue title"
}
```

The handler ignores unrelated triggers, statuses other than `to research`, missing
issue identity/title values, and titles that already start with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
