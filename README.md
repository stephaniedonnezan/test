# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automation payloads.
When an issue status changes to `To Research`, `linear_title_prefix.py` builds an
action that prefixes the issue title with `Cursor researching`.

The handler is intentionally dependency-free:

```bash
python3 -m unittest -v
```

To use it with a JSON payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```
