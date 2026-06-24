# Linear research title prefix

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status changes to `to research`, `linear_title_prefix.py` returns a
title update action that prefixes the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4071",
  "title": "Cursor researching: Add search"
}
```

Non-status updates, other statuses, incomplete payloads, and titles that already
start with `Cursor researching` are ignored.

Run the tests with:

```sh
python3 -m unittest -v
```
