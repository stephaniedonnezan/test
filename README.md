# Linear issue title automation

This repository contains a small handler for Linear status-change automations.

`linear_title_prefix.build_issue_title_update(event)` returns an
`update_issue_title` action when a Linear issue status changes to `to research`.
The action prefixes the issue title with `Cursor researching` and is idempotent:
titles already starting with that prefix are left unchanged.

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4790",
    "title": "Cursor researching: Rename co2 excel export columns (and reorder)",
}
```

Run tests with:

```bash
python3 -m unittest -v
```
