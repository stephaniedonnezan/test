# Linear issue title automation

This repository contains a small handler for Linear status-change automations.

`linear_title_prefix.py` builds an `update_issue_title` action when an issue moves
to the `to research` status. Matching titles are prefixed with
`Cursor researching` unless that prefix is already present.

Run the tests with:

```sh
python3 -m unittest -v
```
