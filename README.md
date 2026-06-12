# Linear issue title prefix automation

This repository contains a small helper for Linear issue automation. When an
issue status changes to `to research`, the helper returns an action to prefix
the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

`build_issue_title_update` is side-effect free and returns `None` when no title
change is needed. Matching events return:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3323",
  "title": "Cursor researching: Existing issue title"
}
```

The module can also be run as a CLI that reads a JSON event from standard input
and prints the update action when one applies.

```bash
python3 linear_title_prefix.py < event.json
```

Run tests with:

```bash
python3 -m unittest -v
```
