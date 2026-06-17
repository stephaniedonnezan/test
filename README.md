# Linear issue title automation

This repository contains a small helper for Cursor/Linear automation payloads.

When a Linear issue status changes to `to research`, `linear_title_prefix.py`
builds an `update_issue_title` action that prefixes the issue title with
`Cursor researching:`.

Example:

```json
{
  "triggerContext": {
    "trigger": "status_changed",
    "newStatus": "To Research",
    "id": "POI-4958",
    "title": "Own Nabisy template currency (version watch)"
  }
}
```

returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4958",
  "title": "Cursor researching: Own Nabisy template currency (version watch)"
}
```

The helper ignores non-status-change events, status changes to other statuses,
and titles that already begin with `Cursor researching`.
