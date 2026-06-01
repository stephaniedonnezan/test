# Linear research title prefix

This repository contains a small helper for Linear status-change automations.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status changes to `To Research`. The action prefixes the issue
title with `Cursor researching` and ignores issues that already have that
prefix.

Run the tests with:

```bash
python3 -m unittest -v
```
