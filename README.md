# Linear issue title research prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler builds an action
that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching events, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5018",
  "title": "Cursor researching: Existing issue title"
}
```

For non-matching events, or for titles that are already prefixed, callers can
safely no-op or use the returned unchanged title.

The module can also be used as a CLI by piping a JSON payload to stdin:

```sh
python3 linear_title_prefix.py < payload.json
```
