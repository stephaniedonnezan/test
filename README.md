# Linear issue title prefix automation

This repository contains a small helper for Linear issue status-change
automations. When an issue moves into `to research`, the helper returns an
`update_issue_title` action that prefixes the title with `Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
