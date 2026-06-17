# Linear research title prefix

This repository contains a small handler for Linear status-change automation
events. When an issue changes status to `to research`, the handler returns an
issue title update that prefixes the title with `Cursor researching`.

## Usage

Pass the Linear event JSON on standard input:

```bash
python3 linear_title_prefix.py < event.json
```

Matching events print an update action:

```json
{"action": "update_issue_title", "issueId": "POI-4973", "title": "Cursor researching: Original title"}
```

Non-matching events produce no output.

## Tests

```bash
python3 -m unittest -v
```
