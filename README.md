# Linear research title prefix automation

This repository contains a small, side-effect-free handler for Cursor/Linear
status change automations.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status changes to `to research`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4579",
  "title": "Cursor researching: MB export corrections"
}
```

Non-status changes, other statuses, missing issue metadata, and titles that
already start with `Cursor researching` return `None`.

## Verify

```bash
python3 -m unittest -v
```
