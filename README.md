# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, `build_issue_title_update` returns an
action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The module can also be used as a CLI that reads a JSON payload from stdin and
prints the update action when one is needed:

```sh
python3 linear_title_prefix.py < payload.json
```
