# Linear research title prefix automation

This repository contains a small, side-effect-free handler for Linear issue
status-change events.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.
Already-prefixed titles are ignored so repeated events do not duplicate the
prefix.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The module also accepts JSON on stdin and writes the update action as JSON:

```bash
python3 linear_title_prefix.py < event.json
```

Run the tests with:

```bash
python3 -m unittest -v
```
