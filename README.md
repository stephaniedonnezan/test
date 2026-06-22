# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action to prefix
the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

If the event should update the issue title, the command prints JSON like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5039",
  "title": "Cursor researching: Hide default emissions section"
}
```

Events that do not represent a status change to `to research`, already have the
prefix, or lack the required issue id/title produce no output.

## Tests

```bash
python3 -m unittest -v
```
