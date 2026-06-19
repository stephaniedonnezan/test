# Linear research title prefix

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an update action that
prefixes the title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The action is `None` unless the event represents a status change to
`to research`, has an issue id and title, and the title is not already prefixed.

The module can also read a JSON event from stdin:

```sh
python3 linear_title_prefix.py < event.json
```

Run tests with:

```sh
python3 -m unittest -v
```
