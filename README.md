# Linear issue title prefix automation

This repository contains a small handler for Linear/Cursor automation payloads.
When an issue status changes to `to research`, it returns an action that prefixes
the issue title with `Cursor researching`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching event, `action` is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4042",
  "title": "Cursor researching: Solve the flake"
}
```

Non-matching events return `None`.

The module also accepts JSON on stdin and prints the computed action:

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
