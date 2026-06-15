# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.
Other issue events return `None`.

Run the tests with:

```bash
python3 -m unittest -v
```
