# Linear issue title prefix automation

This repository contains a small helper for Linear issue automations. When an
issue status-change event moves an issue to `To Research`, the helper returns an
action to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching events, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4718",
  "title": "Cursor researching: Log in issue"
}
```

Events that do not represent a move to `To Research`, or titles that already
start with `Cursor researching`, return `None`.

Run tests with:

```sh
python3 -m unittest -v
```
