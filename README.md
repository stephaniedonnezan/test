# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler returns an
action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching status-change event, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4004",
  "title": "Cursor researching: Make /audit/uuid/mass-balance return correct shape for container sites"
}
```

Events that are not status changes to `to research`, are missing an issue id or
title, or already begin with `Cursor researching` return `None`.

The module also supports stdin JSON for simple CLI use:

```sh
python3 linear_title_prefix.py < event.json
```

Run tests with:

```sh
python3 -m unittest -v
```
