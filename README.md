# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automation payloads.
When a Linear issue status changes to `To Research`, the helper returns an
action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For matching payloads, `update` has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5054",
  "title": "Cursor researching: Select All button for POS issuance"
}
```

Payloads for other statuses, non-status updates, missing issue metadata, or
titles that already start with `Cursor researching` do not create duplicate
prefixes.

## CLI

The module can also read a JSON payload from stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
