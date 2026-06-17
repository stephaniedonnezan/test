# Linear research title prefix automation

This repository contains a small helper for Cursor/Linear issue automations.
When a Linear issue status changes to `to research`, the helper builds an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

The helper intentionally ignores:

- status changes to any other state
- non-status issue updates
- titles that already start with `Cursor researching`
- payloads without an issue id or title

## Usage

Pass a Linear/Cursor webhook payload on standard input:

```sh
python3 linear_title_prefix.py < payload.json
```

For a matching status-change event, the command prints an action such as:

```json
{"action": "update_issue_title", "issueId": "POI-5021", "title": "Cursor researching: Add hydrogen input does not change anything in mass balance"}
```

For non-matching payloads, it prints `null`.

## Tests

```sh
python3 -m unittest -v
```
