# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Linear issue
status-change automation.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action instructing the caller to prefix the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-5010",
        "title": "Mass balance execution (monthly operations)",
    }
)
```

The action shape is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5010",
  "title": "Cursor researching: Mass balance execution (monthly operations)"
}
```

The handler ignores non-status-change events, statuses other than `to research`,
missing issue identifiers or titles, and titles that already start with
`Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
