# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status-change payload moves an issue to `to research`, the helper
returns an action asking the caller to prefix the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

For matching payloads, the CLI prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4885",
  "title": "Cursor researching: unlock qualified outputs"
}
```

Non-matching payloads produce no output. The helper avoids duplicating an
existing `Cursor researching` prefix.
