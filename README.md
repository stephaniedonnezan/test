# Linear title prefix automation

This repository contains a small handler for Linear issue status-change
automation payloads. When an issue moves to `to research`, it builds an action
that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching event, the handler returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4686",
  "title": "Cursor researching: Discuss with Stephanie"
}
```

For non-status-change events, statuses other than `to research`, already
prefixed titles, or invalid payloads, it returns `None`.

The module can also be used as a CLI by passing JSON on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

Run the tests with:

```bash
python3 -m unittest -v
```
