# Linear issue title automation

This repository contains a small handler for Cursor/Linear automation payloads.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The handler is idempotent: titles that already begin with `Cursor researching`
are left unchanged.
