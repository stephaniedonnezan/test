# Linear issue title prefix automation

This repository contains a small, pure Python handler for Linear status-change
automation payloads.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.
Non-matching events return `None`, and titles already starting with that prefix
are left unchanged.

Run tests with:

```sh
python3 -m unittest -v
```
