# Linear issue title automation

This repository contains a small handler for Linear status-change automations.

When an issue status changes to `to research`, `build_issue_title_update` returns
an action to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The module can also be used as a stdin/stdout JSON command:

```bash
python3 linear_title_prefix.py < event.json
```
