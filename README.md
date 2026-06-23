# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear status-change
automation payloads.

`build_issue_title_update(event)` returns an `update_issue_title` action when an
issue status changes to `to research`. The returned title is prefixed with
`Cursor researching:` and existing prefixes are not duplicated.

Run the tests with:

```bash
python3 -m unittest -v
```
