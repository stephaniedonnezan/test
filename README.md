# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action to prefix
the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(payload)
```

The function returns `None` for events that are not status changes to
`to research`, for payloads missing an issue id/title, or when the title already
starts with `Cursor researching`.
