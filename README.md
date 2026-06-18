# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automation payloads.

When an issue changes to `To Research`, `build_issue_title_update` returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "To Research",
        "id": "POI-4832",
        "title": "GoO Cancelation upload supports multiple documents",
    }
)
```

Run tests with:

```sh
python3 -m unittest -v
```
