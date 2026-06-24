# Linear title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action to prefix
the issue title with `Cursor researching`.

Run tests:

```sh
python3 -m unittest -v
```

Run the CLI with a JSON payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```
