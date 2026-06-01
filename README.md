# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action to prefix
the issue title with `Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
