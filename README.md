# Linear research title prefix automation

This repository contains a small helper for Linear issue status-change
automations.

When a Linear issue status changes to `To Research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4249",
  "title": "Cursor researching: Trader: Add dispatch date sanity check"
}
```

The helper ignores unrelated triggers, status changes to other states, and titles
that already begin with `Cursor researching`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(linear_event)
```

The module can also be used as a stdin JSON command:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
