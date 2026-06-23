# Linear research title prefix automation

This repository contains a small handler for Linear status-change automations.
When an issue moves to `to research`, the handler returns an action that prefixes
the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(payload)
```

For a matching payload, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5033",
  "title": "Cursor researching: CO2 inputs optional proof file"
}
```

Non-status changes, statuses other than `to research`, missing issue data, and
titles already beginning with `Cursor researching` return `None`.

The module can also be used as a stdin JSON CLI:

```bash
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```bash
python3 -m unittest -v
```
