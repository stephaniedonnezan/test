# test

## Linear issue title update helper

This repository includes `linear_issue_title.py`, a small helper to derive an updated
issue title for Linear status-change automation payloads.

When the event indicates the issue moved to `to research`, the helper prefixes the
title with `Cursor researching -` (without duplicating existing prefixes).

Run tests with:

```bash
python3 -m unittest -v
```
