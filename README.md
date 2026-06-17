# Linear research title prefix

This repository contains a small, side-effect-free helper for Linear issue
automation.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status-change payload moves the issue to `to research`. The new
title is prefixed with `Cursor researching:` unless it already starts with that
marker.

Run the test suite with:

```bash
python3 -m unittest -v
```
