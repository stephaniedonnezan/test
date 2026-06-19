# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automation events. When an issue moves to `to research`, the handler returns an
action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching event, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4157",
  "title": "Cursor researching: Show unallocated batches"
}
```

Events that are not status changes, statuses other than `to research`, missing
issue metadata, or titles already starting with `Cursor researching` return
`None`.

Run the tests with:

```bash
python3 -m unittest -v
```
