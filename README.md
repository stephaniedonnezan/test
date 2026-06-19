# Linear issue title automation

This repository contains a small handler for Linear status-change automations.

When an issue status changes to `to research`, `linear_title_prefix.py` returns an
`update_issue_title` action that prefixes the title with `Cursor researching`.
Other trigger types or statuses are ignored.

Run the tests with:

```sh
python3 -m unittest -v
```
