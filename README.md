# Linear title prefix automation

This repository contains a small, side-effect-free handler for Linear status
change automation payloads.

When an issue status changes to `to research`, `linear_title_prefix.py` returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`. Other status changes and non-status events return no
action.

Run the tests with:

```bash
python3 -m unittest -v
```
