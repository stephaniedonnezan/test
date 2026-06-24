# Linear issue title prefix helper

This repository contains a small helper for Cursor/Linear automations.  When a
Linear issue status changes to `to research`, the helper returns an action that
prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "To Research",
        "id": "POI-4110",
        "title": "Seeder helper tool",
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4110",
  "title": "Cursor researching: Seeder helper tool"
}
```

The helper ignores non-status updates, statuses other than `to research`, and
titles that already start with `Cursor researching`.

## CLI

The module can also read a JSON event from stdin:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
