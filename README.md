# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when the issue status changes
to `to research`.

Use `build_issue_title_update(event)` from `linear_title_prefix.py` to turn a
Linear/Cursor automation payload into an `update_issue_title` action:

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The module also accepts JSON on stdin and prints the action JSON for simple CLI
integration.
