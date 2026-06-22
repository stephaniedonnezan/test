# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations that need
to update an issue title when the issue moves into research.

## Behavior

`build_issue_title_update(event)` returns an action payload when all of these are
true:

- the event is a status/state change;
- the new status normalizes to `to research`;
- the issue has both an id and title;
- the title does not already begin with `Cursor researching`.

The returned payload has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5043",
  "title": "Cursor researching: Original issue title"
}
```

For non-matching events, the helper returns `None`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The module can also read a JSON payload from stdin:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
