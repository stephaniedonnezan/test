# Linear issue title automation

This repository contains a small handler for Linear issue status-change
automation.

When an issue moves to **To Research**, `build_issue_title_update` returns an
`update_issue_title` action that prefixes the current title with
`Cursor researching`. Non-status changes, other statuses, missing issue data,
and titles that already begin with the marker are ignored.

Run the tests with:

```bash
python3 -m unittest -v
```
