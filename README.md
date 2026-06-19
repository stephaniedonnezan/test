# Linear research title prefix

This repository contains a small handler for Linear/Cursor automation payloads.
When an issue status changes to `to research`, the handler returns an action to
prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching status-change event, `update` is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5033",
  "title": "Cursor researching: CO2 inputs optional proof file"
}
```

Run tests with:

```bash
python3 -m unittest -v
```
