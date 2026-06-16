# Linear issue title research prefix

This repository contains a small handler for Linear issue status-change
automation payloads. When an issue moves to `to research`, the handler returns
an action that prefixes the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

The CLI prints an `update_issue_title` action when the payload should change the
issue title. Non-matching events exit without output.
