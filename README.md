# Linear research title prefix

This repository contains a small helper for Linear/Cursor automation payloads.
When an issue status-change event moves an issue to `to research`, the helper
returns an action that prefixes the issue title with `Cursor researching`.

## Usage

Import `build_issue_title_update` and pass the webhook/automation event:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For matching events the return value is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3476",
  "title": "Cursor researching: Implement Unloading"
}
```

For non-matching events, missing issue details, or titles that already start
with `Cursor researching`, the helper returns `None`.

The module can also be used as a CLI that reads JSON from stdin and prints the
update action when one is needed:

```bash
python3 linear_title_prefix.py < event.json
```

## Testing

```bash
python3 -m unittest -v
```
