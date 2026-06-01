# Linear issue title automation

This repository contains a small helper for Linear status-change automations.

When an issue status changes to `to research`, `linear_title_prefix.py` builds an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
