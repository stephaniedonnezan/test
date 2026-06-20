# Linear issue title prefix helper

This repository contains a small helper for Cursor/Linear automations.

When a Linear issue status changes to `to research`, `linear_title_prefix.py`
builds a title update action that prefixes the issue title with
`Cursor researching`.

Example:

```json
{
  "trigger": "status_changed",
  "newStatus": "to research",
  "id": "POI-4932",
  "title": "Improve the Stored File Transaction Delegate"
}
```

returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4932",
  "title": "Cursor researching: Improve the Stored File Transaction Delegate"
}
```

Run tests with:

```bash
python3 -m unittest -v
```
