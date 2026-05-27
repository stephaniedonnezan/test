# Linear issue title research prefix

This repository contains a small handler for Linear issue status-change
automation. When an issue moves to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(linear_event)
```

Run the focused test suite with:

```bash
python3 -m unittest -v
```
