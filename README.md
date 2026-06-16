# Linear research title prefix

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action that prefixes
the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching events, `action` has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4859",
  "title": "Cursor researching: Existing issue title"
}
```

The handler accepts Cursor's flat `triggerContext` payloads and common nested
Linear issue update payloads. It ignores non-status triggers, status changes to
other states, and titles that already start with `Cursor researching`.

## CLI

The module can also read one JSON event from stdin and print the update action
when one is needed:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
