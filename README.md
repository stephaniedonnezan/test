# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action to update the
issue title with the `Cursor researching` prefix.

## Usage

Pass a Linear automation or webhook event as JSON on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

Matching events print an action payload:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4941",
  "title": "Cursor researching: Move libreoffice to a separate lambda function"
}
```

Events that are not status changes to `to research`, or titles that already
begin with `Cursor researching`, produce no output.

## Tests

```bash
python3 -m unittest -v
```
