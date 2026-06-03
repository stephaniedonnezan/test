# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation events.

When an issue status changes to `to research`, `build_issue_title_update`
returns an `update_issue_title` action that prefixes the issue title with
`Cursor researching`. Other statuses, non-status-change events, missing issue
data, or titles that already start with the prefix are no-ops.

Run the tests with:

```bash
python3 -m unittest -v
```
