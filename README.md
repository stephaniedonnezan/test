# Linear issue title prefix helper

This repository contains a small helper for Cursor/Linear automations.

When an issue status-change event moves an issue to `to research`,
`linear_title_prefix.py` returns the title update needed to prefix the issue
title with `Cursor researching:`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
if update:
    # Map update["issueId"] and update["title"] into the Linear client.
    ...
```

The helper is side-effect free. It only returns an update payload when all of
these are true:

- the event is a status-change event, or an issue update with a status/state
  changed-field marker
- the new status normalizes to `to research`
- the issue has a non-empty id and title
- the title is not already prefixed with `Cursor researching`

It can also be used from the command line by passing a JSON event on stdin:

```bash
python3 linear_title_prefix.py < event.json
```
