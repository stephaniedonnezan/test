# Linear issue title research prefix

This repository contains a small handler for Linear issue status-change
automation. When an issue moves to `To Research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(payload)
```

The handler returns `None` when the payload is not a status change, the new
status is not `To Research`, the title is already prefixed, or required issue
fields are missing.

Run tests with:

```bash
python3 -m unittest -v
```
