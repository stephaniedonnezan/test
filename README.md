# Linear research title prefix

This repository contains a small helper for Linear issue status-change
automations. When an issue moves to `to research`, the helper returns an action
that prefixes the issue title with `Cursor researching`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The returned action is either `None` or:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4914",
  "title": "Cursor researching: Existing title"
}
```

Run tests with:

```bash
python3 -m unittest -v
```
