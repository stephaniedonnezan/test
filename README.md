# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to the `to research` status, the handler
builds an action to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a qualifying status change, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4965",
  "title": "Cursor researching: original issue title"
}
```

For non-status changes, statuses other than `to research`, or titles that
already start with `Cursor researching`, the handler returns `None`.

Run tests with:

```shell
python3 -m unittest -v
```
