# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, `build_issue_title_update` returns an
`update_issue_title` action that prefixes the title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The handler ignores unrelated status changes and titles that already begin with
`Cursor researching`.
