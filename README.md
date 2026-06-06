# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves an issue to `To Research`, the handler
builds an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching event, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4839",
  "title": "Cursor researching: Existing issue title"
}
```

Events that do not represent a status change to `To Research`, or issues whose
titles already start with `Cursor researching`, return `None`.

## CLI

The module can also be used as a stdin/stdout JSON command:

```bash
python3 linear_title_prefix.py < event.json
```

The CLI prints the update action and exits `0` when a title update is needed. It
prints nothing and exits `1` when no title update should be made.

## Tests

```bash
python3 -m unittest -v
```
