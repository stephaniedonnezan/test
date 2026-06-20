# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action to prefix the
issue title with `Cursor researching`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The returned action is either:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4826",
  "title": "Cursor researching: Update container allocation data"
}
```

or `None` when the event is not a status change to `to research`, required issue
data is missing, or the title already starts with `Cursor researching`.

The module can also be used as a CLI by piping a JSON payload to stdin:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
