# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation events.
When a Linear issue status changes to `To Research`, the handler returns an
action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

result = build_issue_title_update(event)
```

For matching events, `result` is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5057",
  "title": "Cursor researching: Existing issue title"
}
```

For non-matching events, missing data, or titles that already start with
`Cursor researching`, the handler returns `None`.

You can also pipe a JSON event to the module:

```sh
python3 linear_title_prefix.py < event.json
```
