# Linear issue research title automation

This repository contains a small handler for Linear issue status-change
automation.

When a Linear issue moves to `to research`, `build_issue_title_update` returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`. Events for other statuses, non-status changes, missing
issue data, or already-prefixed titles are ignored.

```bash
python3 -m unittest -v
```
