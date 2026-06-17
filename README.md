# Linear title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, `linear_title_prefix.py` emits an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run the test suite with:

```bash
python3 -m unittest -v
```
