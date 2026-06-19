# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status changes to `to research`, the handler returns an action to
prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4878",
            "title": "LPH enablement even if no BOP",
        }
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4878",
  "title": "Cursor researching: LPH enablement even if no BOP"
}
```

Run tests with:

```bash
python3 -m unittest -v
```
