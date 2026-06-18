# Linear issue title research prefix

This repository contains a small helper for Linear issue automations.

When an issue status-change event moves an issue to `to research`, the helper
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4425",
  "title": "Cursor researching: []Rounding logic"
}
```

The helper accepts flat Cursor automation payloads, such as `triggerContext`
objects, and common nested Linear webhook shapes under `data`, `issue`, or
`data.issue`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

From the command line, pass a JSON payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

No output means the event does not need a title update.

## Tests

```sh
python3 -m unittest -v
```
