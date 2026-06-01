# Linear research title prefix automation

This repository contains a small handler for Linear status-change automation
payloads.

When an issue status changes to `to research`, `linear_title_prefix.py` returns
an `update_issue_title` action that prefixes the issue title with
`Cursor researching`. Payloads for other statuses or already-prefixed titles are
ignored.

Run the tests with:

```bash
python3 -m unittest -v
```
