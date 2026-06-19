# Linear issue title automation

This repository contains a small helper for Linear issue webhooks triggered by
Cursor automations.

`linear_title_prefix.py` exposes `build_issue_title_update(event)`, which
returns an `update_issue_title` action when a Linear issue status changes to
`to research`. The generated title is prefixed with `Cursor researching: ` and
existing `Cursor researching` prefixes are not duplicated.

The helper accepts Cursor's flat `triggerContext` payloads as well as nested
Linear issue update payloads. It can also be run as a CLI by passing a JSON
payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```sh
python3 -m unittest -v
```
