# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automations.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status changes to `to research`. The generated title is prefixed
with `Cursor researching` and existing prefixes are not duplicated.

Run the test suite with:

```bash
python3 -m unittest -v
```
