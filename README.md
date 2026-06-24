# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation events.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status-change event moves an issue to `to research`. The returned
title is prefixed with `Cursor researching:` unless it already has that prefix.

Run the test suite with:

```sh
python3 -m unittest -v
```
