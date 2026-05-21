# Linear issue title automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, it returns an action that
prefixes the issue title with `Cursor researching`.

Run the test suite with:

```sh
python3 -m unittest -v
```
