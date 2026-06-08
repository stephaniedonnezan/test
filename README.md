# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automation events.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4849",
  "title": "Cursor researching: Make Filters Visible"
}
```

The handler ignores unrelated triggers, statuses other than `to research`, and
titles that already start with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
