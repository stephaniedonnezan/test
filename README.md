# Linear issue title prefix automation

This repository contains a small webhook helper for Cursor/Linear automations.
When a Linear issue status changes to `to research`, it builds an update action
that prefixes the issue title with `Cursor researching`.

Run the tests with:

```bash
python3 -m unittest -v
```
