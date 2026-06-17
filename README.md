# Linear research title prefix

This repository contains a small helper for Cursor/Linear automations.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status changes to `to research`. The generated title is prefixed
with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5041",
  "title": "Cursor researching: Supply contracts are not only inputting producer"
}
```

Non-status changes, statuses other than `to research`, and titles already
starting with `Cursor researching` return `null`/`None`.

Run the test suite with:

```bash
python3 -m unittest -v
```
