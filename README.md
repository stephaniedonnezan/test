# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `to research`, the handler returns an
action to prefix the issue title with `Cursor researching`.

## Usage

Pass the webhook or automation payload as JSON on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

When the payload represents a status change into `to research`, the script
prints an update action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3171",
  "title": "Cursor researching: \"undo\" document upload"
}
```

Payloads that do not match the trigger produce no output.

## Tests

```bash
python3 -m unittest -v
```
