# Linear issue title prefix helper

This repository contains a small helper for Linear status-change automations.
When an issue moves to `to research`, `linear_title_prefix.py` builds an
`update_issue_title` action that prefixes the title with `Cursor researching`.

Example:

```bash
python3 linear_title_prefix.py --input payload.json
```

For a payload containing `trigger: "status_changed"`, `newStatus: "to research"`,
an issue id, and a title, the script prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4266",
  "title": "Cursor researching: Revisit UX of Delivery Linking Dialog"
}
```
