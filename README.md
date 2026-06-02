# Linear research title prefix

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `To Research`, `build_issue_title_update` returns an
action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The module also supports stdin/stdout JSON usage:

```sh
python3 linear_title_prefix.py < event.json
```
