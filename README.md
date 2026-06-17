# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation payloads.

When an issue status changes to `to research`, `linear_title_prefix.py` returns
an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4997",
  "title": "Cursor researching: Local meter supplier uuid says optional but is mandatory"
}
```

Run the tests with:

```bash
python3 -m unittest -v
```
