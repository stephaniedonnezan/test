# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automation events.
When a Linear issue status changes to `to research`, the handler returns a
data-only action to prefix the issue title with `Cursor researching`.

Run tests with:

```bash
python3 -m unittest -v
```
