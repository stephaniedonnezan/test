# Linear issue title prefix automation

This repository contains a small, side-effect-free helper for Linear issue
status-change automations. When an issue moves to `to research`, the helper
builds an action payload that adds `Cursor researching` to the beginning of the
issue title.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching event, `action` is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4817",
  "title": "Cursor researching: Existing issue title"
}
```

The handler accepts the flat Cursor `triggerContext` shape as well as nested
Linear issue update webhook payloads. It ignores non-status events, statuses
other than `to research`, missing issue data, and titles that already start with
`Cursor researching`.

## CLI

The module can also read an event JSON document from stdin:

```bash
python3 linear_title_prefix.py < event.json
```

It prints the update action as JSON, or `null` when no title update is needed.

## Tests

```bash
python3 -m unittest -v
```
