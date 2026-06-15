# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status changes to `to research`, the handler returns a data-only
action to update the Linear issue title with the `Cursor researching` prefix.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching event, the return value is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4937",
  "title": "Cursor researching: Existing issue title"
}
```

For non-matching events, invalid payloads, or titles that already start with the
prefix, the handler returns `None`.

## CLI

The module can also read a JSON payload from stdin and print the update action:

```sh
python3 linear_title_prefix.py < payload.json
```

## Tests

```sh
python3 -m unittest -v
```
