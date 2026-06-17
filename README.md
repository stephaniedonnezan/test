# Linear research title prefix

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status changes to `To Research`, `build_issue_title_update(event)`
returns an action to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The helper returns `None` for unrelated events, non-research statuses, or titles
that already start with `Cursor researching`.
