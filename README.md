# Linear issue title prefix automation

This repository contains a small automation helper for Linear status-change
events. When an issue moves to `To Research`, the helper returns an action that
adds `Cursor researching` to the beginning of the issue title.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching event, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4325",
  "title": "Cursor researching: Existing title"
}
```

For non-status changes, statuses other than `To Research`, or titles that
already start with `Cursor researching`, the function returns `None`.

The module can also read a JSON event from stdin:

```bash
python3 linear_title_prefix.py < event.json
```

Run the tests with:

```bash
python3 -m unittest -v
```
