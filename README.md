# Linear title prefix automation

This repository contains a small Cursor automation helper for Linear issue
status changes.

When an issue status-change event moves an issue to `to research`, the helper
returns an `update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run the test suite with:

```sh
python -m unittest test_linear_title_prefix.py
```
