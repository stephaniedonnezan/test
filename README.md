# Linear research title prefix

This repository contains a small helper for Cursor/Linear automation payloads.
When an issue status changes to `to research`, the helper builds an action that
adds `Cursor researching` to the beginning of the issue title.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching status transition, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3860",
  "title": "Cursor researching: Meter table should display sites"
}
```

For non-matching events, missing issue data, or titles that already start with
`Cursor researching`, it returns `None`.

The module can also read a JSON event from stdin:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
