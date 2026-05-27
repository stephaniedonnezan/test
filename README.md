# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation events.
When a Linear issue status changes to `to research`, the handler requests a title
update that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the command prints an action like:

```json
{"action": "update_issue_title", "issueId": "POI-4533", "title": "Cursor researching: Original title"}
```

Events that do not represent a status change to `to research`, or titles that
already start with `Cursor researching`, produce no output.
