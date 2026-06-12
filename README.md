# Linear research title prefix

This repository contains a small handler for Cursor automation events from
Linear. When an issue status changes to `to research`, the handler returns an
action asking the caller to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The function returns `None` unless all of the following are true:

- the event represents a status change;
- the new status normalizes to `to research`;
- the issue has an id and title; and
- the title does not already start with `Cursor researching`.

For manual checks, pass a JSON event to the module on stdin:

```sh
python3 linear_title_prefix.py < event.json
```
