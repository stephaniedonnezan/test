# Linear issue research title automation

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status changes to `to research`, the handler returns an action to
prefix the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For matching events, the script prints:

```json
{"action": "update_issue_title", "issueId": "POI-4728", "title": "Cursor researching: Existing title"}
```

Non-matching events produce no output.

## Test

```bash
python3 -m unittest -v
```
