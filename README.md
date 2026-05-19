# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automation.

When a Linear issue status changes to `To Research`, `linear_title_prefix.py`
builds an `update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

If the payload does not represent a status change to `To Research`, or the title
already starts with `Cursor researching`, the command exits successfully without
printing an update action.
