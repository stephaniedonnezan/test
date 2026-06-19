# Linear issue title automation

This repository contains a small dependency-free handler for Linear issue
status-change events. When an issue moves to `to research`, the handler returns
an `update_issue_title` action that prefixes the title with
`Cursor researching`.

```bash
python3 -m unittest -v
```

The handler can also be used as a JSON-in/JSON-out CLI step:

```bash
python3 linear_title_prefix.py < event.json
```
