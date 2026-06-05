# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Linear issue
status-change automations.

When an issue status changes to `To Research`, `build_issue_title_update(event)`
returns an action payload that asks the runner to prefix the issue title with
`Cursor researching`. Non-matching events return `None`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The module can also be used as a CLI that reads a JSON event from stdin. Matching
events print the update payload and exit `0`; non-matching events exit `1`.

```bash
python3 linear_title_prefix.py < event.json
python3 -m unittest -v
```
