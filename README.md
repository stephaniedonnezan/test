# Linear research title prefix

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status change moves the issue to `to research`, the helper returns
an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-4809",
        "title": "Reduce number of entityManager.save to one.",
    }
)

assert action == {
    "action": "update_issue_title",
    "issueId": "POI-4809",
    "title": "Cursor researching: Reduce number of entityManager.save to one.",
}
```

The helper accepts flat Cursor trigger contexts and nested Linear-style issue
update payloads. It ignores unrelated updates, ignores statuses other than
`to research`, and does not add a duplicate `Cursor researching` prefix.

You can also pipe a JSON payload into the module:

```bash
python3 linear_title_prefix.py < payload.json
```
