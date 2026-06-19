# Linear research title prefix

This repository contains a small helper for Linear automation payloads.

When an issue status-change event moves an issue to `to research`, the helper
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4009",
  "title": "Cursor researching: Add Select field on Delivery Form"
}
```

The helper is side-effect free. It can be imported with
`build_issue_title_update(event)` or used as a CLI that reads a JSON payload from
stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```sh
python3 -m unittest -v
```
