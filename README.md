# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `to research`, the handler builds an issue
title update that prefixes the current title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For matching events, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-123",
  "title": "Cursor researching: Existing issue title"
}
```

For non-matching events, missing issue data, or titles that already start with
`Cursor researching`, it returns `None`.
