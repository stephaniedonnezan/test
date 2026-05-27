# Linear issue title research automation

This repository contains a small handler for Linear status-change automation
events. When an issue moves to `To Research`, the handler returns an action to
prefix the issue title with `Cursor researching`.

```bash
python3 -m unittest -v
```
