# Linear issue title prefix automation

This repository contains a small decision helper for Cursor/Linear automations.
When an issue status-change event moves to `to research`, the helper returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching:`.

Run tests with:

```sh
python3 -m unittest -v
```
