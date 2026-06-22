# Linear research title prefix automation

This repository contains a small handler for Linear issue webhooks. When an
issue status changes to `to research`, the handler returns an action to prefix
the issue title with `Cursor researching`.

## Usage

Call `build_issue_title_update(event)` from `linear_title_prefix.py` with the
Linear/Cursor automation payload:

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching status-change events, the return value is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3765",
  "title": "Cursor researching: Existing issue title"
}
```

For all other events, or for titles that already start with `Cursor researching`,
the handler returns `None`.

You can also pipe a JSON event to the module:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
