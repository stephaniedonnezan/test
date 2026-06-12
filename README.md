# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an
`update_issue_title` action that prefixes the title with `Cursor researching`.

Run tests with:

```sh
python3 -m unittest -v
```

The module can also read a JSON event from stdin and print the update action:

```sh
python3 linear_title_prefix.py < event.json
```
