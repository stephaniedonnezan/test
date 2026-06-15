# Linear research title prefix

This repository contains a small handler for Linear status-change automation.

`build_issue_title_update(event)` returns an `update_issue_title` action when an
issue status changes to `to research`. The generated title is prefixed with
`Cursor researching: ` and existing `Cursor researching` prefixes are left
unchanged.

Run the test suite with:

```bash
python3 -m unittest -v
```
