# Linear research title prefix automation

This repository contains a small dependency-free helper for Linear/Cursor
automation payloads. When an issue status changes to `to research`, the helper
builds an action payload that prefixes the issue title with `Cursor researching`.

## Usage

Pass a JSON event on stdin:

```sh
python3 linear_title_prefix.py < event.json
```

For matching status-change events, the command prints:

```json
{"action": "update_issue_title", "issueId": "POI-123", "title": "Cursor researching: Existing title"}
```

For non-matching events, it exits successfully without output.
