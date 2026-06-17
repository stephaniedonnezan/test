# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automations.

When a Linear issue status changes to `To Research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4995",
  "title": "Cursor researching: Trader site creation"
}
```

The handler ignores unrelated status changes, non-status triggers, and titles
that already begin with `Cursor researching`.

## Run tests

```sh
python3 -m unittest -v
```
