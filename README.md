# Linear issue title prefix automation

This repository contains a small side-effect-free handler for Linear issue
status-change events. When an issue moves to `to research`, the handler returns
an action instructing the caller to prefix the issue title with
`Cursor researching`.

Run tests with:

```bash
python3 -m unittest -v
```
