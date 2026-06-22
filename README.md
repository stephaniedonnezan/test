# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status changes to `to research`. The action prefixes the title with
`Cursor researching` and skips issues that are already prefixed.

Run the test suite with:

```bash
python3 -m unittest -v
```
