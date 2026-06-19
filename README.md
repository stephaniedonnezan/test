# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automation payloads.

When an issue status changes to `to research`, `build_issue_title_update(event)`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4307",
  "title": "Cursor researching: Spreadsheet app agnostic for testing"
}
```

The handler is idempotent and returns `None` when the title already starts with
`Cursor researching`.

## CLI

Pass a JSON payload on stdin to print the update action, when one is needed:

```sh
python3 linear_title_prefix.py < payload.json
```

## Tests

```sh
python3 -m unittest -v
```
