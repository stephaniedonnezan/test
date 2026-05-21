# Linear issue title prefix

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status-change event moves an issue to `to research`, the helper
returns an action that updates the issue title to start with
`Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
