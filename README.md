# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Cursor/Linear
automation payloads.

When a Linear issue status changes to `to research`, `linear_title_prefix.py`
returns an action instructing the caller to prefix the issue title with
`Cursor researching`. Titles that already start with that prefix are ignored so
the automation does not duplicate it.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching status-change event, the command prints:

```json
{"action": "update_issue_title", "issueId": "POI-5014", "title": "Cursor researching: Wrong font and color and field height on Add input dialog"}
```

Non-matching events produce no output.

## Tests

```bash
python3 -m unittest -v
```
