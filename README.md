# Linear title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.

When a Linear issue status changes to `To Research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(payload)
```

The function returns `None` for unrelated triggers, statuses other than
`To Research`, or titles that already start with `Cursor researching`.
