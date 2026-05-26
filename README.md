# Linear issue title research prefix

This repository contains a small handler for Linear issue status change
automation. When an issue is moved to `To Research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run the test suite with:

```sh
python3 -m unittest -v
```
