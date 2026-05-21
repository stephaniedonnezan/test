# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Linear issue
status-change automation events.

When an issue status changes to `to research`, `build_issue_title_update`
returns an `update_issue_title` action that prefixes the issue title with
`Cursor researching`. The handler ignores other statuses, non-status-change
events, missing issue data, and titles that already have the prefix.

Run the tests with:

```bash
python3 -m unittest -v
```
