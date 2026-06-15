# Linear research title prefix automation

This repository contains a small helper for Cursor/Linear automations that adds
`Cursor researching` to an issue title when the issue status changes to
`to research`.

## Usage

Import `build_issue_title_update` and pass the automation event payload:

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

When the event qualifies, the function returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3942",
  "title": "Cursor researching: Define internal JSON schema"
}
```

For non-matching events, malformed payloads, or titles that already start with
`Cursor researching`, it returns `None`.

The module can also be used as a CLI by piping a JSON event to stdin:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
