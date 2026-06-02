# Linear research title prefix

This repository contains a small automation helper for Linear issue status-change
events. When an issue moves to `to research`, `linear_title_prefix.py` builds an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
