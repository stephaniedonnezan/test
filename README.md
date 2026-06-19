# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status changes to **To Research**, the helper builds an issue title
update action that prefixes the existing title with `Cursor researching`.

The core entry point is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It accepts either the flat Cursor automation
`triggerContext` shape or a nested Linear webhook-style payload.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update({
    "trigger": "status_changed",
    "newStatus": "To Research",
    "id": "POI-5020",
    "title": "Issues should always try to link",
})

assert action == {
    "action": "update_issue_title",
    "issueId": "POI-5020",
    "title": "Cursor researching: Issues should always try to link",
}
```

The module can also be used as a simple CLI that reads a JSON event from stdin
and prints the title update action, or `null` when no update is required.

```bash
python3 linear_title_prefix.py < event.json
```
