# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler returns an
action to prefix the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The script prints a JSON action when the issue title should be updated:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4320",
  "title": "Cursor researching: Existing title"
}
```

If the payload is not a status change to `to research`, or the title is already
prefixed, the script exits without output.

## Tests

```bash
python3 -m unittest -v
```
