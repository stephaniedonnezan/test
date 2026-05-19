# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations.

When an issue status changes to `to research`, `build_issue_title_update(event)`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4719",
  "title": "Cursor researching: Shell cannot log into app.atmen.co"
}
```

The handler ignores non-status-change events, status changes to other states,
payloads without an issue id or title, and titles that already start with
`Cursor researching`.

Run tests with:

```sh
python3 -m unittest -v
```
