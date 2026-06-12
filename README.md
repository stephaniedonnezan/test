# Linear issue title automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler produces an
issue-title update action that prefixes the title with `Cursor researching`.

The handler is intentionally side-effect free: callers pass in the webhook or
automation event payload, and the handler returns either an update action or
`None`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-2309",
        "title": "The CO2 emissions units are hardcoded",
    }
)

assert action == {
    "action": "update_issue_title",
    "issueId": "POI-2309",
    "title": "Cursor researching: The CO2 emissions units are hardcoded",
}
```

Run the tests with:

```bash
python3 -m unittest -v
```
