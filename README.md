# Linear issue title prefix automation

This repository contains a small helper for Linear status-change automations.

`linear_title_prefix.py` exposes `build_issue_title_update(event)`, which returns
an issue-title update action only when an issue status changes to `to research`.
The returned title is prefixed with `Cursor researching: ` and titles that
already start with `Cursor researching` are ignored.

Run the tests with:

```bash
python3 -m unittest -v
```
