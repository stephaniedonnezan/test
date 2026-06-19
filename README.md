# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status changes to `To Research`, the helper returns an idempotent
title update that prefixes the issue title with `Cursor researching`.

## Usage

Pass a Linear or Cursor automation event JSON payload on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

When the event is a supported status-change event moving an issue to
`To Research`, the script emits:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4963",
  "title": "Cursor researching: User role & rights cannot be seen by invitee"
}
```

For events that should not change the title, it emits `{}`.
