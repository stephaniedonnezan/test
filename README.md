# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automation events.

When an issue moves to `to research`, `build_issue_title_update(event)` returns
an action that prefixes the issue title with `Cursor researching`. Events for
other statuses, non-status changes, missing issue data, or titles that already
start with the prefix are ignored.

Run the test suite with:

```bash
python3 -m unittest -v
```
