# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automation events. When
a Linear issue status changes to `to research`, the helper returns an action to
prefix the issue title with `Cursor researching`.

## Usage

Pass a JSON event on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

For matching status-change events, the script prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4076",
  "title": "Cursor researching: Fix failing Cypress tests on main"
}
```

For events that should not update the title, it prints `null`.

## Tests

```bash
python3 -m unittest -v
```
