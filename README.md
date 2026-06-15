# Linear issue title prefix helper

This repository contains a small helper for Cursor/Linear automations.

When a Linear issue status-change payload moves an issue to `to research`, the
helper builds an idempotent title update that prefixes the issue title with
`Cursor researching`.

## Usage

Pipe a JSON payload into the CLI:

```sh
python3 linear_title_prefix.py < payload.json
```

The script prints either an update action:

```json
{"action": "update_issue_title", "issueId": "POI-4935", "title": "Cursor researching: Original title"}
```

or `null` when the payload does not require a title change.

## Tests

```sh
python3 -m unittest -v
```
