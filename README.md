# Linear title prefix automation

This repository contains a small helper for Linear issue automations. When an
issue status-change payload moves an issue to `to research`, the helper returns
an action to prefix the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

Example output:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3878",
  "title": "Cursor researching: CO2 inputs missing from November mass balance"
}
```

Payloads for other statuses, non-status updates, or titles that already start
with `Cursor researching` return `null`.
