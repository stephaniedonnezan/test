# Linear issue title prefix automation

This repository contains a small helper for Cursor-triggered Linear issue
automation.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status changes to `To Research`. The returned title is prefixed with
`Cursor researching:` and existing `Cursor researching` prefixes are left
unchanged.

Run the tests with:

```sh
python3 -m unittest -v
```
