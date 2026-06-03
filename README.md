# Linear title prefix automation

This repository contains a small helper for Cursor automations triggered by
Linear issue status changes. When a Linear issue moves to `to research`, the
helper emits an `update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run the test suite with:

```sh
python3 -m unittest -v
```
