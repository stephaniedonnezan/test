# Linear issue title prefix automation

This repository contains a small helper for Linear status-change automations.

When an issue status changes to `to research`, `linear_title_prefix.py` builds an
`update_issue_title` action that prefixes the issue title with
`Cursor researching:`. Non-status changes, other statuses, and titles that are
already prefixed are ignored.

## Usage

Pass a Linear/Cursor automation event as JSON on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

Matching events print a JSON action:

```json
{"action": "update_issue_title", "issueId": "POI-4790", "title": "Cursor researching: Rename co2 excel export columns (and reorder)"}
```

Events that do not match print nothing.

## Tests

```bash
python3 -m unittest -v
```
