# Linear research title prefix

This repository contains a small handler for Cursor automations triggered by
Linear issue status changes.

When an issue status changes to `to research`, the handler emits a title update
action that prefixes the existing title with `Cursor researching:`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-123",
  "title": "Cursor researching: Existing issue title"
}
```

The handler ignores non-status-change events, statuses other than `to research`,
missing issue identifiers/titles, and titles that already begin with
`Cursor researching`.

## Usage

Pass the webhook payload as JSON on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

If no title update is required, the command exits successfully without output.

## Tests

```sh
python3 -m unittest -v
```
