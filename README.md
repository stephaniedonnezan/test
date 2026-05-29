# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `To Research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The handler returns `None` for non-matching statuses, non-status-change events,
missing issue metadata, or titles that already start with `Cursor researching`.
