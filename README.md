# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

Run the tests with:

```bash
python3 -m unittest -v
```
