# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves an issue to `to research`, the handler
returns an action to prefix the issue title with `Cursor researching`.

```bash
python3 -m unittest -v
```
