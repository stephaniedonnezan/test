# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves to `to research`, it returns an action
that prefixes the Linear issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4442",
  "title": "Cursor researching: Existing issue title"
}
```

Events that are not status changes, statuses other than `to research`, missing
issue IDs/titles, or titles already starting with `Cursor researching` return
`null`.

## Usage

Pass a Cursor/Linear webhook payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

Or import the handler:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(payload)
```

## Test

```bash
python3 -m unittest -v
```
