# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an `update_issue_title` action that prefixes the issue title with
`Cursor researching`. Non-matching status changes, non-status events, and titles
that already have the prefix are ignored.

The module can also be used as a CLI by passing the JSON event on stdin:

```sh
python3 linear_title_prefix.py < event.json
```
