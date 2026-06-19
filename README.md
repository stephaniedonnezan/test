# Linear research title prefix

This repository contains a small helper for Cursor/Linear automations.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status changes to `to research`. The returned title is prefixed
with `Cursor researching` unless that prefix is already present.

Run the tests with:

```bash
python3 -m unittest -v
```

The helper can also read an event payload from stdin:

```bash
python3 linear_title_prefix.py < event.json
```
