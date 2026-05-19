# Linear issue title prefix automation

Adds a small handler for Linear status-change automation payloads. When an issue
is moved to `To Research`, the handler returns an `update_issue_title` action
that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

If the event is not a status change to `To Research`, or the title already starts
with `Cursor researching`, the handler returns `None`.
