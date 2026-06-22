# Linear research title prefix

This repository contains a small helper for Linear status-change automations.

`linear_title_prefix.py` reads a Linear/Cursor automation payload and builds an
issue title update only when the issue status changes to `to research`. Matching
issues receive the prefix:

```text
Cursor researching: <existing title>
```

Titles that already start with `Cursor researching` are left unchanged.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

When an update is required, the command prints JSON in this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5045",
  "title": "Cursor researching: Existing issue title"
}
```

## Tests

```bash
python3 -m unittest -v
```
