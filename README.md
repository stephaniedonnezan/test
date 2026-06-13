# Linear title prefix automation

This repository contains a small handler for Cursor automation events from Linear.

`build_issue_title_update(event)` returns an `update_issue_title` action when an
issue status-change event moves to `to research`. The generated title is prefixed
with `Cursor researching:` and existing prefixes are left unchanged.

Run the tests with:

```bash
python3 -m unittest -v
```
