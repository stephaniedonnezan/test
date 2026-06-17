# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.

When a Linear/Cursor issue payload indicates that an issue moved to `to research`,
`build_issue_title_update(event)` returns an action that prefixes the title with
`Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4962",
  "title": "Cursor researching: User role not persisiting upon invitation"
}
```

The handler ignores non-status changes, non-`to research` statuses, malformed
payloads, and titles that already begin with `Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
