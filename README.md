# Linear issue title prefix automation

This repository contains a small dependency-free handler for Linear issue
status-change automation.

When an issue status changes to `to research`, `build_issue_title_update` returns
an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The module also supports a JSON stdin CLI:

```bash
python3 linear_title_prefix.py < event.json
```
