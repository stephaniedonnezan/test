# Linear research title prefix automation

This repository contains a small handler for Linear status-change automation
payloads. When an issue status changes to `to research`, the handler requests a
title update that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For matching payloads, the script prints an action object:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4748",
  "title": "Cursor researching: Existing issue title"
}
```

Non-matching payloads produce no output.

## Tests

```bash
python3 -m unittest -v
```
