# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automation.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.
Events for other statuses, non-status updates, missing issue data, or titles
that already start with `Cursor researching` return no action.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "issueId": "POI-4896",
        "title": "Cool refactor to push straight to main - `SiteFrame`",
    }
)
```

The same handler can be used as a command-line filter:

```bash
python3 linear_title_prefix.py < event.json
```

Run tests with:

```bash
python3 -m unittest -v
```
