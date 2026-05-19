# Linear issue title automation

This repository contains a small handler for Cursor Automation payloads from
Linear. When an issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
