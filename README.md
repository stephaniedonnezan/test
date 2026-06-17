# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automation
payloads. When an issue moves to `To Research`, the handler returns an action
that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the script prints an action such as:

```json
{"action": "update_issue_title", "issueId": "POI-5003", "title": "Cursor researching: Trading vs Production Filter not filtering"}
```

Non-matching events produce no output.
