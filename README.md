# Linear research title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status changes to `to research`, the helper returns an action to
prefix the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4528",
  "title": "Cursor researching: Performance improvement for graph traversal"
}
```

The helper is idempotent: issues whose titles already start with
`Cursor researching` are ignored.

## Usage

Pass a JSON event on stdin:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
