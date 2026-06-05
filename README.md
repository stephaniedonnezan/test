# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status-change event moves an issue to `to research`, the
handler returns an action to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The module can also be used as a JSON stdin/stdout CLI:

```bash
python3 linear_title_prefix.py < payload.json
```

Matching payloads print an `update_issue_title` action. Non-matching payloads
print `null`.
