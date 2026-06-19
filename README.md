# Linear research title prefix

This repository contains a small helper for Linear status-change automations.
When an issue moves to `to research`, `build_issue_title_update` returns an
action describing the title update needed to prefix the issue with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

Matching events return:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4322",
  "title": "Cursor researching: Refine the storage loss dialog"
}
```

The helper accepts Cursor's flat `triggerContext` payloads and nested Linear
webhook payloads. It ignores non-status updates, statuses other than
`to research`, invalid payloads, and titles that already begin with
`Cursor researching`.

Run tests with:

```bash
python3 -m unittest -v
```
