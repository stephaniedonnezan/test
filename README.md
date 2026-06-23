# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
payloads. When an issue moves to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run it from stdin with a JSON payload:

```bash
python3 linear_title_prefix.py < payload.json
```

Run the tests with:

```bash
python3 -m unittest -v
```
