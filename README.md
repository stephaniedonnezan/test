# Linear research title prefix automation

This repository contains a small handler for Linear status-change automations.

When an issue status changes to `to research`, `build_issue_title_update(event)`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4947",
  "title": "Cursor researching: Post-download next-steps guide + lead nurture sequence"
}
```

The handler accepts flat Cursor automation payloads and common nested Linear
webhook payloads. It ignores unrelated events and skips titles that already
start with `Cursor researching`.
