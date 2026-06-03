# Linear research title prefix automation

This repository contains a small handler that prepares a Linear issue title
update when an issue status changes to `to research`.

## Behavior

- Matches status-change events whose new status normalizes to `to research`.
- Prefixes the issue title as `Cursor researching: <existing title>`.
- Skips non-matching statuses, non-status-change triggers, missing issue data,
  and titles that already begin with `Cursor researching`.

## Usage

Import the pure function:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

Or pipe a JSON payload into the CLI:

```bash
python3 linear_title_prefix.py < payload.json
```

Matching payloads print an action like:

```json
{"action": "update_issue_title", "issueId": "POI-4793", "title": "Cursor researching: Blocked delivery 7872"}
```
