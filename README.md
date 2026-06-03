# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
payloads. When an issue moves to `to research`, the handler returns an action
that updates the issue title to start with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The function returns `None` when the event is not a matching status change, the
new status is not `to research`, the issue title is already prefixed, or the
payload does not include enough issue information.

Run the tests with:

```sh
python3 -m unittest -v
```
