# Linear issue title automation

This repository contains a small, side-effect-free helper for Linear issue
status-change automations.

When a status-change event moves an issue to `to research`,
`build_issue_title_update` returns an action that prefixes the issue title with
`Cursor researching`. Other events return `None`.

```python
from linear_issue_title import build_issue_title_update

action = build_issue_title_update(event)
```
