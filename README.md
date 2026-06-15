# Linear issue title prefix

This repository contains a small handler for Linear status-change automation.
When an issue moves to `to research`, `build_issue_title_update` returns an
action that prefixes the issue title with `Cursor researching`.

Run the tests with:

```bash
python3 -m unittest -v
```
