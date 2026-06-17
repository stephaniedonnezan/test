# Linear issue title prefix helper

This repository contains a small helper for Cursor/Linear automation payloads.
When a Linear issue status change moves an issue to `to research`, the helper
returns an action that prefixes the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
python3 -m unittest -v
```
