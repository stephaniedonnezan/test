# Linear research title prefix

This repository contains a small, side-effect-free helper for Linear status
change automations. When an issue status changes to `To Research`, the helper
builds an action to prefix the issue title with `Cursor researching`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(
    {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3877",
            "title": "Production site legal entity address",
        }
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3877",
  "title": "Cursor researching: Production site legal entity address"
}
```

The module also supports stdin JSON for simple automation wiring:

```bash
python3 linear_title_prefix.py < payload.json
```

If the payload is not a status-change event moving to `To Research`, or the
title already starts with `Cursor researching`, no update is emitted.
