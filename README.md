# Linear issue title automation

This repository contains a small helper for Cursor/Linear automation payloads.

When a Linear issue status-change event moves an issue to `To Research`,
`build_issue_title_update` returns an action that prefixes the issue title with
`Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5039",
  "title": "Cursor researching: Default emissions do not trickle down"
}
```

The helper ignores other status changes, non-status issue updates, and titles
that already start with `Cursor researching`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(payload)
```

The module can also read a JSON payload from stdin and print the generated
action:

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
