# Linear research title prefix automation

This repository contains a small handler for Linear status change automation.

When an issue changes status to `To Research`, `linear_title_prefix.py` returns
an `update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run tests with:

```bash
python3 -m unittest -v
```
