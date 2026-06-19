# Linear issue title prefix

This repository contains a small helper for Linear status-change automations.

`linear_title_prefix.py` exposes `build_issue_title_update(event)`, which returns an
`update_issue_title` action when a Linear issue moves to `to research`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4491",
  "title": "Cursor researching: N+1 Query"
}
```

Events that are not status changes to `to research`, or titles already starting
with `Cursor researching`, return `None`.
