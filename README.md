# Linear issue title automation

This repository contains a small helper for Cursor/Linear automations.

`linear_title_prefix.py` reads a Linear issue status-change payload and returns
an update action only when the issue moves to `to research`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5031",
  "title": "Cursor researching: Improve performance of timeZoneObject()"
}
```

The helper is side-effect free and avoids adding the `Cursor researching` prefix
when the title already starts with it.
