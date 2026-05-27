# Linear research title prefix

This repository contains a small helper for Cursor automations that react to
Linear issue status changes.

When an issue status change moves an issue to `to research`, the helper returns
an action requesting the issue title be updated to:

```text
Cursor researching: <current title>
```

The helper is side-effect free: callers pass the Linear/Cursor event payload to
`build_issue_title_update(event)` and apply the returned action if it is not
`None`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
