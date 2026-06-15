# Linear research title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status changes to `to research`, the helper builds an issue-title
update action that prefixes the existing title with `Cursor researching`.

## Usage

Pass the automation payload as JSON on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

For a matching status-change event, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4205",
  "title": "Cursor researching: Auditor observation period"
}
```

Non-matching events produce no output. Titles that already start with
`Cursor researching` are ignored so the prefix is not duplicated.

## Tests

```sh
python3 -m unittest -v
```
