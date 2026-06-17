# Linear research title prefix

This repository contains a small automation helper for Linear issue events. When
an issue status changes to `to research`, the helper returns an action requesting
that the issue title be prefixed with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching status-change payload, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4886",
  "title": "Cursor researching: get qualified outputs"
}
```

For non-matching events, or titles that already start with `Cursor researching`,
it returns `None`.

The module can also be used as a CLI that reads a JSON event from stdin:

```sh
python3 linear_title_prefix.py < event.json
```

Run tests with:

```sh
python3 -m unittest -v
```
