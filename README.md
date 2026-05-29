# Linear issue title automation

Adds `Cursor researching` to a Linear issue title when a status-change event moves
the issue to `to research`.

The Python helper reads a Linear automation/webhook-style payload and returns an
issue title update action:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The helper returns `None` for unrelated status changes, non-status-change
events, missing issue data, or titles that already start with
`Cursor researching`.
