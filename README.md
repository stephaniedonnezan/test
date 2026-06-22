# Linear title prefix automation

This repository contains a small helper for Cursor/Linear automations.

When a Linear issue status-change event moves an issue to `to research`,
`linear_title_prefix.py` prepares a title update that prefixes the issue title
with `Cursor researching:`. Events for other statuses are ignored, and titles
that already start with `Cursor researching` are left unchanged.

Run it as a CLI by piping the webhook event JSON to stdin:

```sh
python3 linear_title_prefix.py < event.json
```

When an update is needed, the script writes JSON like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5073",
  "title": "Cursor researching: Backend e2e to test scenarios is escapable by user"
}
```
