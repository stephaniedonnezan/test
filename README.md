# Linear issue title prefix automation

This repository contains a small, side-effect-free helper for Linear issue
status-change automations.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`:

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-4588",
        "title": "Methane closing warnings are merging",
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4588",
  "title": "Cursor researching: Methane closing warnings are merging"
}
```

The helper ignores other status changes, non-status-change events, and titles
that already begin with `Cursor researching`.

Run tests with:

```sh
python3 -m unittest -v
```
