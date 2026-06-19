# Linear research title prefix

This repository contains a small helper for Linear issue status-change
automations. When an issue status changes to `to research`, the helper returns
an action instructing the caller to update the issue title with the
`Cursor researching` prefix.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3869",
            "title": "Quick win: Turn2X feedback - counter reading bad request",
        }
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3869",
  "title": "Cursor researching: Quick win: Turn2X feedback - counter reading bad request"
}
```

No action is returned for other statuses, non-status-change events, missing
issue metadata, or titles that already start with `Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
