# Linear issue research title automation

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves an issue to `To Research`, the handler
returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The function returns `None` when no title update is needed. It also avoids
duplicating the prefix when the title already starts with `Cursor researching`.

Run the tests with:

```bash
python3 -m unittest -v
```
