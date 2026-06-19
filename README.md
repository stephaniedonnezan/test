# Linear issue title automation

This repository contains a small helper for Linear issue automation.

`linear_title_prefix.py` builds an `update_issue_title` action when a Linear
issue status changes to `to research`. The generated title is prefixed with
`Cursor researching` unless the title already has that marker.

Run tests with:

```sh
python3 -m unittest -v
```
