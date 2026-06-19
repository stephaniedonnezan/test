# Linear research title prefix automation

This repository contains a small, side-effect-free helper for Cursor/Linear
automations.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.
Non-matching events return `None`, and titles that already start with the prefix
are ignored.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The module can also be used as a CLI by piping a JSON event to stdin:

```sh
python3 linear_title_prefix.py < event.json
```
