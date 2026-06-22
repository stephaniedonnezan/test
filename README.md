# Linear issue title prefix automation

This repository contains a small, dependency-free helper for Linear automation
webhooks.

When an issue status-change event moves to `to research`, `linear_title_prefix`
builds an action that adds the title prefix `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3875",
  "title": "Cursor researching: Existing title"
}
```

The helper accepts both flat Cursor `triggerContext` payloads and common nested
Linear webhook shapes. It returns no action for non-status changes, other target
statuses, missing issue metadata, or titles that already start with
`Cursor researching`.

Run tests with:

```bash
python3 -m unittest -v
```
