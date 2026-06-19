# Linear issue title research prefix

This repository contains a small JSON-in/JSON-out helper for Linear issue
automation.

When an issue status-change event moves to `to research`,
`build_issue_title_update` returns an action that prefixes the issue title with
`Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5077",
  "title": "Cursor researching: QA report - POI-4878 LPH without BOP"
}
```

Non-status events, status changes to other states, and titles that already start
with `Cursor researching` return no action.

Run tests with:

```bash
python3 -m unittest -v
```
