# Linear title prefix automation

This repository contains a small handler for Linear status-change automations.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.
Other status changes and non-status events are ignored.

Run the tests with:

```sh
python3 -m unittest -v
```
