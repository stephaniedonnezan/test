# Linear issue title prefix automation

This repository contains a small helper for Linear/Cursor automation payloads.
When an issue status changes to `to research`, `build_issue_title_update(event)`
returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

Matching events return:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4885",
  "title": "Cursor researching: unlock qualified outputs"
}
```

Non-matching events return `None`. Existing titles that already start with
`Cursor researching` are ignored to avoid duplicate prefixes.

## CLI

The helper can also read a JSON event from stdin:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
