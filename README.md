# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automations.
When a Linear issue changes status to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update
```

The module can also be used as a CLI that reads a JSON event from stdin and
prints the resulting action, or `null` when no title change is needed:

```bash
python3 linear_title_prefix.py < event.json
```

Run the tests with:

```bash
python3 -m unittest -v
```
