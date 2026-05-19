# Linear issue research title prefix

This repository contains a small automation helper for Linear issue status
changes.

`linear_title_prefix.py` exposes `build_issue_title_update(event)`, which returns
an `update_issue_title` action when a Linear issue status changes to
`to research`. The new title is prefixed with `Cursor researching` unless that
prefix is already present.

Run tests with:

```sh
python3 -m unittest -v
```
