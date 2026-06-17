# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations.

`linear_title_prefix.py` reads a Linear issue status-change payload and emits an
`update_issue_title` action when the issue moves to `To Research`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4970",
  "title": "Cursor researching: Existing issue title"
}
```

The helper normalizes status casing/separators, supports flat Cursor
`triggerContext` payloads and nested Linear issue payloads, and avoids adding the
`Cursor researching` prefix more than once.

Run the tests with:

```sh
python3 -m unittest -v
```
