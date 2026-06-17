# Linear research title prefix

This repository contains a small handler for Linear status-change automations.
When an issue changes status to `to research`, the handler returns an action to
prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching events, `action` is shaped like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5039",
  "title": "Cursor researching: Default emissions do not trickle down"
}
```

Non-status-change events, statuses other than `to research`, and already
prefixed titles return `None`.

Run tests with:

```sh
python3 -m unittest -v
```
