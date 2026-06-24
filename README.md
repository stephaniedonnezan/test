# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run tests with:

```sh
python3 -m unittest -v
```
