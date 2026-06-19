# Linear issue title prefix helper

This repository contains a small handler for Linear issue status-change events.

When an issue status changes to `to research`, `linear_title_prefix.py` builds an
idempotent title-update action that prefixes the issue title with
`Cursor researching`.

## Usage

Pass a JSON event payload on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

The script prints either an update action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4620",
  "title": "Cursor researching: Move tests from cypress to backend tests"
}
```

or `null` when the payload should not update the issue title.

## Tests

```bash
python3 -m unittest -v
```
