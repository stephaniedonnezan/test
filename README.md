# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear issue automation.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status-change payload moves an issue to `to research`. The returned
title is prefixed with `Cursor researching` and existing prefixes are left alone.

Run the tests with:

```sh
python3 -m unittest -v
```
