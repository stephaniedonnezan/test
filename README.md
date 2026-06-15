# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.

When an issue status changes to `to research`, `build_issue_title_update` returns
an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4907",
  "title": "Cursor researching: Refactor for main"
}
```

Events that are not status changes, statuses other than `to research`, missing
issue identifiers or titles, and titles that already start with
`Cursor researching` return `null`.

## Usage

Run the handler as a CLI by piping a JSON event to stdin:

```bash
python3 linear_title_prefix.py < event.json
```

Run the tests with:

```bash
python3 -m unittest -v
```
