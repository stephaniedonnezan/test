# Linear research title prefix

This repository contains a small helper for Cursor automations triggered by
Linear issue status changes.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with:

```text
Cursor researching: <original title>
```

The helper safely no-ops for other status changes, non-status events, missing
issue metadata, and titles that already start with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The CLI prints the computed action as JSON, or `null` when no title update is
needed.

## Tests

```bash
python3 -m unittest -v
```
