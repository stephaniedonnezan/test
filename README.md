# Linear issue title research marker

This repository contains a small helper for Linear automations. When a Linear
issue status changes to `To Research`, `linear_title_prefix.py` builds an
`update_issue_title` action that prefixes the issue title with:

```text
Cursor researching:
```

The helper is idempotent and skips titles that already start with
`Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The script prints the update action as JSON for matching payloads and prints
nothing for events that should not update the issue title.
