# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

Matching payloads print an action shaped like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4962",
  "title": "Cursor researching: User role not persisiting upon invitation"
}
```

Non-matching payloads produce no output.
