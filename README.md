# Linear research title prefix

This repository contains a small side-effect-free helper for Linear issue
automation.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status-change payload moves to `To Research`. The generated title
is prefixed with `Cursor researching` and existing prefixes are left unchanged.

Run the test suite with:

```sh
python3 -m unittest -v
```
