# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler returns an
action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching payloads, `action` has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4703",
  "title": "Cursor researching: Existing title"
}
```

Non-matching payloads return `None`. The module also accepts JSON on stdin and
prints either the action JSON or `null`.

Run tests with:

```sh
python3 -m unittest -v
```
