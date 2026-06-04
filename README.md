# Linear research title prefix automation

This repository contains a small, side-effect-free handler for Linear issue
status-change payloads. When an issue moves to `to research`, the handler
builds an issue-title update that prefixes the title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

Matching payloads print an `update_issue_title` action. Non-matching payloads
print `null`.
