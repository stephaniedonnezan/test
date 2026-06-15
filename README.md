# Linear research title prefix

This repository contains a small, side-effect-free helper for Linear issue
status-change automations.

When a Linear issue status changes to `To Research`, `build_issue_title_update`
returns an action describing the title update that should be applied:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4545",
  "title": "Cursor researching: Existing issue title"
}
```

Events that are not status changes, do not move to `To Research`, are missing an
issue ID or title, or already begin with `Cursor researching` return `null`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

The module can also be used as a JSON stdin CLI for smoke testing:

```sh
python3 linear_title_prefix.py < event.json
```

## Verification

```sh
python3 -m unittest -v
```
