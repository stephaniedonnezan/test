# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation payloads. When an issue moves to `to research`, the handler builds
an update action that prefixes the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

The command prints an `update_issue_title` action for matching payloads and
exits without output for non-matching payloads.
