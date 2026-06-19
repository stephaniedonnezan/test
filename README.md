# Linear research title prefix

This repository contains a small, side-effect-free helper for Linear status-change
automations.

`linear_title_prefix.py` exposes `build_issue_title_update(event)`, which returns
an `update_issue_title` action when a Linear issue moves to `to research`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5045",
  "title": "Cursor researching: Supply contract only states producer"
}
```

The helper accepts Cursor Cloud `automation_trigger_info.triggerContext` payloads,
flat trigger contexts, and nested Linear issue update webhook payloads. It ignores
non-status updates, non-research statuses, and titles already prefixed with
`Cursor researching`.
