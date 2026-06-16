# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler returns an
action that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For matching payloads, the command prints an action object:

```json
{"action": "update_issue_title", "issueId": "POI-3982", "title": "Cursor researching: Original title"}
```

Payloads for other status changes, non-status triggers, or titles that already
begin with `Cursor researching` do not produce an action.

## Tests

```bash
python3 -m unittest -v
```
