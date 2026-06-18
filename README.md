# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves an issue into `to research`, the handler
emits an action that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The CLI prints either an update action:

```json
{"action": "update_issue_title", "issueId": "POI-4932", "title": "Cursor researching: Example title"}
```

or `null` when the payload should be ignored.

## Tests

```bash
python3 -m unittest -v
```
