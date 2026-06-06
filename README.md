# Linear title status helper

This repository contains a small helper for Linear automation payloads. When an
issue status-change event moves an issue to `to research`, the helper derives an
updated title with the `Cursor researching` marker:

```text
Cursor researching - Existing issue title
```

Run the tests with:

```bash
python3 -m unittest
```
