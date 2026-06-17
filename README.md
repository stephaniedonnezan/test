# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action to prefix the
issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5015",
  "title": "Cursor researching: Power allocation"
}
```

The handler is intentionally side-effect free: callers pass in the webhook event
and apply the returned action in the surrounding automation runner.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

No output is printed when the event should not update the issue title.

## Tests

```bash
python3 -m unittest -v
```
