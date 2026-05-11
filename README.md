# Linear issue title automation

This repository contains a small handler for Linear status-change automation.

When an issue status changes to `To Research`, `linear_title_prefix.py` emits an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
