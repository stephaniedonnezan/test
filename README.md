# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action that prefixes
the title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

event = {
    "triggerContext": {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-4521",
        "title": "Check transport emissions stay working",
    }
}

build_issue_title_update(event)
# {
#     "action": "update_issue_title",
#     "issueId": "POI-4521",
#     "title": "Cursor researching: Check transport emissions stay working",
# }
```

The handler returns `None` when the event is not a status change, the new status
is not `to research`, or the title already starts with `Cursor researching`.

Run tests with:

```sh
python3 -m unittest -v
```
