# Linear issue title automation

This repository contains a small utility used by automation to enforce issue-title
conventions when a Linear issue status changes.

## Behavior implemented

- If an issue transitions to status `to research`, the title is updated to start
  with `Cursor researching: `.
- Prefixing is idempotent (the prefix is not added twice).
- Status matching is case/whitespace insensitive.

## Usage

Pipe a Linear webhook payload JSON to the script:

```bash
python linear_issue_title.py < payload.json
```

The script emits JSON like:

```json
{
  "issue_id": "POI-4464",
  "should_update": true,
  "new_title": "Cursor researching: delivery event and unloading event bug"
}
```

## Tests

```bash
python -m unittest -v
```
