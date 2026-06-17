# Linear issue title prefix automation

This repository contains a small helper for Linear issue status-change automations.

When a Linear issue changes status to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5007",
  "title": "Cursor researching: Weird formatting of sentence with link"
}
```

Other statuses and non-status-change events return `null`. Titles that already
start with `Cursor researching` are left unchanged.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
