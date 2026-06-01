# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automation payloads.

When an issue status changes to `to research`, the handler returns an action to
prefix the issue title with `Cursor researching`.

Run tests with:

```sh
python3 -m unittest -v
```
