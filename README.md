# Linear issue title prefix automation

This repository contains a small handler for Linear issue webhooks/automation
payloads. When an issue status changes to `to research`, the handler returns an
action to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The handler returns `None` for unrelated events, statuses other than
`to research`, or titles that already start with `Cursor researching`.
