# Linear research title prefix

This repository contains a small helper for Cursor/Linear automations. When an
issue status-change event moves an issue to `to research`, the helper returns an
`update_issue_title` action that prefixes the title with `Cursor researching`.

Run the tests with:

```bash
python3 -m unittest -v
```
