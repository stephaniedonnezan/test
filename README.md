# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `to research`, the handler returns an
action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching event, `action` has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4798",
  "title": "Cursor researching: Rename the sites and org names in the methane demo"
}
```

Non-matching events return `None`, including status changes to any status other
than `to research` and titles that already start with `Cursor researching`.
