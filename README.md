# Linear research title prefix

Small helper for Cursor/Linear automations that marks issues when they move to
research.

When a Linear issue status-change payload indicates the new status is
`to research`, `build_issue_title_update(event)` returns an action that prefixes
the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

Example action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4321",
  "title": "Cursor researching: Meters - New reading doesn't appear in list until page refresh"
}
```

The helper returns `None` for unrelated triggers, other statuses, invalid issue
payloads, or titles that already start with `Cursor researching`.

Run tests with:

```bash
python3 -m unittest -v
```
