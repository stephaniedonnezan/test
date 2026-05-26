# Linear issue title automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `To Research`, the handler returns an `update_issue_title`
action that prefixes the issue title with `Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
