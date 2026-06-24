# Linear research title prefix

This repository contains a small helper for Cursor automations that react to
Linear issue status changes.

When an issue status changes to `to research`, `build_issue_title_update`
returns an `update_issue_title` action that prefixes the title with
`Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
