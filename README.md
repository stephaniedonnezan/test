# Linear issue title prefix automation

This repository contains a small, side-effect free helper for Linear/Cursor
automation payloads. When an issue status-change event moves an issue to
`to research`, `linear_title_prefix.py` returns an action that prefixes the
issue title with `Cursor researching`.

Run the tests with:

```bash
python3 -m unittest -v
```
