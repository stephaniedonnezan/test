# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation events.
When a Linear issue status changes to `to research`, the handler returns an
action payload that prefixes the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4969",
  "title": "Cursor researching: Unexpected star icon when linking deliveries"
}
```

The handler ignores other status changes, generic issue updates that did not
change a status field, missing issue data, and titles that already start with
`Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

If the event does not require a title update, the command exits successfully
without printing an action.

## Tests

```bash
python3 -m unittest -v
```
