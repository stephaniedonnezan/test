# Linear research title prefix automation

This repository contains a small helper for Linear status-change automations.
When an issue is moved to `to research`, it emits an action that prefixes the
issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

Matching payloads print an action object:

```json
{"action": "update_issue_title", "issueId": "POI-4772", "title": "Cursor researching: Existing title"}
```

Non-matching payloads do not print anything.
