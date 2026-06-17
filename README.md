# Linear title prefix automation

This repository contains a small helper for Cursor/Linear automations.

When a Linear issue status changes to `to research`, `linear_title_prefix.py`
builds an issue-title update action that prefixes the title with
`Cursor researching`. Other status changes, unrelated updates, and issues that
already have the prefix are ignored.

Run the tests with:

```bash
python3 -m unittest -v
```
