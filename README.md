# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automations.

When an issue status changes to `to research`, `build_issue_title_update`
returns an `update_issue_title` action that prefixes the title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The module can also be used as a CLI by passing a JSON event on stdin. It prints
the update action only when the event should change the issue title.
