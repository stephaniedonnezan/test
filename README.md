# Linear research title prefix

This repository contains a small dependency-free handler for Linear issue
status-change automations.

When an issue status changes to `To Research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching event, the return value is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4939",
  "title": "Cursor researching: 2026-06-15-DailyReport"
}
```

Non-status changes, statuses other than `To Research`, missing issue metadata,
and titles that already start with `Cursor researching` return `None`.

The module can also read a JSON payload from stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```sh
python3 -m unittest -v
```
