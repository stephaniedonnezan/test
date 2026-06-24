# Linear issue title research automation

This repository contains a small, side-effect-free handler for Linear issue
status-change events.

When an issue status changes to `to research`, `linear_title_prefix.py` returns
an `update_issue_title` action that prefixes the issue title with
`Cursor researching`. Events for other status changes, non-status triggers,
missing issue metadata, or titles that already have the prefix are ignored.

Run the tests with:

```bash
python3 -m unittest -v
```
