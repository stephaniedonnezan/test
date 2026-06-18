# Linear research title prefix automation

This repository contains a small helper for Cursor/Linear automations.

When a Linear issue status-change payload moves an issue to `to research`,
`linear_title_prefix.py` builds an update action that prefixes the issue title
with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The module also accepts JSON on stdin and prints the action when an update is
needed:

```sh
python3 linear_title_prefix.py < event.json
```

Run the tests with:

```sh
python3 -m unittest -v
```
