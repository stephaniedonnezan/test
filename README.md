# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to the `to research` status, the handler builds an action to
prefix the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For a matching event, the script prints an action like:

```json
{"action": "update_issue_title", "issueId": "POI-3551", "title": "Cursor researching: Front end implementation"}
```

Non-matching events produce no output.

## Tests

```bash
python3 -m unittest -v
```
