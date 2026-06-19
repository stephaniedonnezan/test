# Linear issue title prefix automation

Adds a `Cursor researching` prefix to a Linear issue title when the issue status
changes to `to research`.

## Usage

The handler accepts either the compact Cursor automation trigger payload or a
nested Linear webhook payload:

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4890",
            "title": "Create",
        }
    }
)
```

When the event is a matching status change, the result is:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4890",
    "title": "Cursor researching: Create",
}
```

The handler returns `None` for non-status changes, statuses other than
`to research`, missing issue data, or titles that already start with
`Cursor researching`.

## Test

```bash
python3 -m unittest -v
```
