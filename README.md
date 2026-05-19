# Linear issue title automation

This repository contains a small handler for Linear issue status-change events.

When an issue moves to `to research`, `linear_title_prefix.py` returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`. Other status changes are ignored, and existing prefixes
are not duplicated.

Run the tests with:

```sh
python3 -m unittest -v
```
