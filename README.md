# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations that marks
issues as being researched by Cursor.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4974",
  "title": "Cursor researching: User removal flow"
}
```

The helper ignores other status changes and avoids adding the prefix when the
title already starts with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

Run tests with:

```bash
python3 -m unittest -v
```
