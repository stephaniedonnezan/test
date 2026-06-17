# Linear issue title automation

This repository contains a small handler for Cursor/Linear status-change
automations. When a Linear issue moves to `to research`, the handler returns an
action that prefixes the issue title with `Cursor researching`.

## Usage

Pass the Linear webhook or Cursor automation payload as JSON on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

For matching status changes, the script prints an update action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4977",
  "title": "Cursor researching: Auditor can access Producer page"
}
```

For non-matching events, it prints `null`.

## Tests

```bash
python3 -m unittest -v
```
