# Linear issue title automation

This repository contains a small helper for Cursor/Linear automation payloads.

`linear_title_prefix.py` builds an `update_issue_title` action when an issue
status-change event moves to `To Research`. The resulting title is prefixed with
`Cursor researching` unless that prefix is already present.

Run the test suite with:

```sh
python3 -m unittest -v
```
