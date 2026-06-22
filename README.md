# Linear issue title prefix helper

This repository contains a small helper for Cursor/Linear automation payloads.

`linear_title_prefix.py` exposes `build_issue_title_update(event)`, which returns
an `update_issue_title` action when a Linear issue status changes to
`to research`. Matching titles are prefixed as:

```text
Cursor researching: <original title>
```

Already-prefixed titles are ignored so the automation is idempotent.

## CLI usage

The module can also read a JSON event from standard input:

```sh
printf '%s\n' '{"trigger":"status_changed","newStatus":"to research","id":"POI-4776","title":"LHV plan 7-9"}' \
  | python3 linear_title_prefix.py
```
