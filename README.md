# Linear research title prefix automation

This repository contains a small handler for Linear status-change automation.
When an issue moves to `to research`, the handler builds an action that prefixes
the issue title with `Cursor researching`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

`build_issue_title_update(event)` returns either:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3259",
  "title": "Cursor researching: design MVP"
}
```

or `None` when the webhook is not a status change into `to research`, the title
already starts with `Cursor researching`, or the issue id/title is missing.

The module also supports a stdin JSON smoke-test mode:

```bash
python3 linear_title_prefix.py < payload.json
```

## Verification

```bash
python3 -m unittest -v
```
