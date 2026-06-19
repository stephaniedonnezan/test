# Linear issue title prefix helper

This repository contains a small helper for Linear status-change automations.
When an issue status changes to `to research`, the helper returns an
`update_issue_title` action that prefixes the title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(
    {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5058",
            "title": "Move the mb-data-manager into the psqo module",
        }
    }
)
```

The result is transport-neutral so an automation can pass it to the Linear
update mechanism it owns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5058",
  "title": "Cursor researching: Move the mb-data-manager into the psqo module"
}
```

The helper is idempotent and returns `None` for non-status triggers, statuses
other than `to research`, missing issue data, or titles that already start with
`Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
