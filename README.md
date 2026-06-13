# Linear research title prefix

This repository contains a small side-effect-free helper for Linear status-change
automation. When an issue status changes to `to research`, it builds an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

## Usage

Pass a Linear webhook or Cursor automation event as JSON on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

If the event is a status change to `to research`, the script prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3431",
  "title": "Cursor researching: Existing issue title"
}
```

Events for other statuses, non-status changes, missing titles, or titles that
already start with `Cursor researching` produce no output.

## Tests

```bash
python3 -m unittest -v
```
