# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, it builds an issue title
update action that prefixes the title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching payload, the handler returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4517",
  "title": "Cursor researching: Existing title"
}
```

For all non-matching payloads it returns `None`. Existing titles that already
begin with `Cursor researching` are left unchanged.

## CLI

The module can also read a JSON payload from stdin and print the update action:

```sh
python3 linear_title_prefix.py < payload.json
```

## Tests

```sh
python3 -m unittest -v
```
