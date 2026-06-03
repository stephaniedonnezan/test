# Linear research title prefix

This repository contains a small handler for Linear issue webhooks. When an
issue status-change payload moves an issue to `to research`, the handler emits
an `update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run the unit tests with:

```bash
python3 -m unittest -v
```
