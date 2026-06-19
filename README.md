# Linear research title prefix

This repository contains a small automation helper for Linear status-change events.

When an issue status changes to `to research`, `linear_title_prefix.py` builds an
issue-title update action that prefixes the current title with `Cursor researching`.
The amount of input validation is intentionally narrow: non-status changes,
non-research statuses, missing issue data, and titles that are already prefixed are
ignored.

## Usage

Pass a JSON webhook payload on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

If the payload qualifies, the script prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4009",
  "title": "Cursor researching: Add Select field on Delivery Form"
}
```

If the payload does not qualify, the script exits successfully without output.

## Tests

```bash
python3 -m unittest -v
```
