# Linear Research Title Prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `To Research`, the handler builds an
issue-title update action that prefixes the existing title with
`Cursor researching`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

`build_issue_title_update` returns either:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4932",
  "title": "Cursor researching: Existing issue title"
}
```

or `None` when no title update is needed.

The module can also read a JSON event from stdin:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
