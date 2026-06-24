# Linear research title prefix

This repository contains a small handler for Linear issue status-change events.
When an issue moves to the `to research` status, the handler returns an action
that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4252",
            "title": "Better strategy in the mapAllRows to choose the mapper",
        }
    }
)
```

The returned action is side-effect free:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4252",
  "title": "Cursor researching: Better strategy in the mapAllRows to choose the mapper"
}
```

The handler ignores unrelated triggers, non-research statuses, missing issue
metadata, and titles that already start with `Cursor researching`.

## CLI

The module can also read a JSON event from stdin and print the action:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

Run the unit tests with:

```bash
python3 -m unittest -v
```
