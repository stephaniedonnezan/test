# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation payloads.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.
Other status changes, non-status updates, and titles that already start with
that prefix are ignored.

Run tests with:

```sh
python3 -m unittest -v
```
