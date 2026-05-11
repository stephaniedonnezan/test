# Linear research title prefix

Small helper for Cursor/Linear automations that need to prefix issue titles
when an issue status changes to `to research`.

The helper reads common Cursor automation trigger payloads and Linear webhook
payloads, then returns an `update_issue_title` action with the `Cursor
researching` prefix when appropriate.

```bash
python linear_title_prefix.py < event.json
```
