# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automations.

When an issue status changes to `to research`, `build_issue_title_update`
returns an update instruction that prefixes the issue title with
`Cursor researching`. Other status changes, non-status triggers, and titles
that already start with the prefix are ignored.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The module can also be used as a stdin JSON CLI:

```sh
python3 linear_title_prefix.py < event.json
```
