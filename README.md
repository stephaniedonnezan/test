# Linear title prefix automation

This repository contains a small side-effect-free handler for Linear issue
status-change automations.

When an issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`. Other triggers or statuses return `None`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The module also supports a simple stdin JSON CLI:

```bash
python3 linear_title_prefix.py < event.json
```
