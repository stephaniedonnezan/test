# Linear issue title prefix automation

This repository contains a small helper for Linear issue status-change
automations. When an issue moves to `to research`, the helper returns an action
that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching events, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5053",
  "title": "Cursor researching: Grey batches allocation issues"
}
```

For non-status-change events, other statuses, missing issue metadata, or titles
that already start with `Cursor researching`, it returns `None`.

The module can also be used as a stdin/stdout JSON CLI:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
