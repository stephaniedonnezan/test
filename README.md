# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler returns an
action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching payloads, `action` has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5039",
  "title": "Cursor researching: Default emissions do not trickle down"
}
```

Payloads that do not represent a status transition to `to research` return
`None`. Existing `Cursor researching` prefixes are preserved without adding a
duplicate prefix.

## CLI

The module can also read a JSON payload from stdin and print the action:

```sh
python3 linear_title_prefix.py < payload.json
```

## Tests

Run the unit tests with:

```sh
python3 -m unittest -v
```
