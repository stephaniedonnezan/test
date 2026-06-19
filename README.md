# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status changes to `to research`, the handler returns an action that
prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

If the payload represents a matching status change, the command prints a compact
JSON action:

```json
{"action":"update_issue_title","issueId":"POI-3626","title":"Cursor researching: Existing title"}
```

Non-matching payloads produce no output.

## Tests

```bash
python3 -m unittest -v
```
