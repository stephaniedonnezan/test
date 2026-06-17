# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler requests that the issue title
be prefixed with `Cursor researching`.

## Usage

Pass a JSON event on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the script prints an update action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5034",
  "title": "Cursor researching: Supply contracts (foundation for inputs/meters)"
}
```

Events that are not status changes to `to research`, or titles that already
start with `Cursor researching`, produce no output.

## Tests

Run the unit tests with:

```bash
python3 -m unittest -v
```
