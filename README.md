# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Linear/Cursor
automation payloads.

When an issue status-change event moves an issue to `to research`, the handler
returns an action to prefix the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5017",
  "title": "Cursor researching: Existing issue title"
}
```

The handler ignores non-status triggers, statuses other than `to research`, and
titles that already start with `Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
