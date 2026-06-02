# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation. When an issue moves to `to research`, it builds an action that
prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching payload, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4770",
  "title": "Cursor researching: Refactor IEmissionFactor"
}
```

For unrelated triggers, non-research statuses, or titles that already start
with `Cursor researching`, it returns `None`.

The module can also be used as a CLI that reads the JSON event from stdin and
prints the update action when one is needed:

```sh
python3 linear_title_prefix.py < event.json
```

Run tests with:

```sh
python3 -m unittest -v
```
