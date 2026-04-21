# Linear issue title automation

This repository includes a small helper for Linear status-change automation.

## Behavior

When an issue event is a status change and the new status is **"to research"**,
the helper returns an update payload that prefixes the issue title with
`Cursor researching`.

- Prefix applied: `Cursor researching: <original title>`
- Duplicate protection: if the title already starts with
  `Cursor researching` (case-insensitive), no update is returned.

## Files

- `linear_title_prefix.py` – event handling and title update payload builder
- `test_linear_title_prefix.py` – unit tests

## Run tests

```bash
python3 -m unittest -v
```
