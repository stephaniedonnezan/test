# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automations.

When an issue status changes to `to research`, `build_issue_title_update(event)`
returns a declarative action that prefixes the issue title with
`Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4751",
  "title": "Cursor researching: Knowledge support on a POS-related question"
}
```

The handler ignores other statuses, non-status-change events, and titles that
already start with `Cursor researching`.

## Development

Run the unit tests with:

```bash
python3 -m unittest -v
```
