# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue status changes to `to research`, the handler returns an action to
update the issue title to include the `Cursor researching` prefix.

## Usage

Import `build_issue_title_update` and pass a Linear/Cursor automation payload:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The function returns `None` for events that should not update the issue. For a
matching issue it returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5024",
  "title": "Cursor researching: Avoiding MB reopening"
}
```

The module can also read a JSON payload from stdin:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

Run the test suite with:

```bash
python3 -m unittest -v
```
