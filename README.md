# Linear issue title automation

This repository contains a small handler for Linear status-change automations.

When an issue status changes to `To Research`, `build_issue_title_update`
returns an `update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4689",
            "title": "Use transaction entity manager",
        }
    }
)
```

The same handler can be used from the command line by piping a JSON event to it:

```sh
python3 linear_title_prefix.py < event.json
```

Run tests with:

```sh
python3 -m unittest -v
```
