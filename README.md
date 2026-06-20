# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations.

When a Linear issue status-change event moves an issue to `to research`,
`linear_title_prefix.py` returns an action that prefixes the issue title with
`Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5018",
  "title": "Cursor researching: Error alert with repeating txt"
}
```

For all other events, the helper returns `null`.

Run the tests with:

```bash
python3 -m unittest -v
```
