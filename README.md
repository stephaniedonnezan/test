# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automations.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.
Non-matching status changes, non-status events, incomplete payloads, and titles
that already have the prefix are ignored.

Run the tests with:

```sh
python3 -m unittest -v
```
