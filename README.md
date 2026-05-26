# Linear issue title prefix automation

This repository contains a small helper for Linear status-change automations.

When an issue status changes to `to research`, `build_issue_title_update` returns an
`update_issue_title` action that prefixes the title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The helper accepts the flat automation trigger payload shape as well as nested
Linear webhook payloads, normalizes status casing/separators, and avoids adding
the prefix twice.
