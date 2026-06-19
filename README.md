# Linear issue title prefix automation

This repository contains a small handler for Linear/Cursor automation payloads.
When an issue status-change event moves an issue to `to research`, the handler
returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

Matching events return:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4520",
  "title": "Cursor researching: Do we need a frontend?"
}
```

Unrelated events, non-research statuses, invalid issue payloads, and titles that
already start with `Cursor researching` return `None`.

## Development

Run tests with:

```bash
python3 -m unittest -v
```

The module can also read a JSON payload from stdin and print the update action:

```bash
python3 linear_title_prefix.py < payload.json
```
