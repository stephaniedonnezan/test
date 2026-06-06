# Linear issue title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves an issue to **To Research**, the handler
builds a title-update action that prefixes the issue title with
`Cursor researching`.

Run the tests:

```sh
python3 -m unittest -v
```

Run the handler with a JSON payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```
