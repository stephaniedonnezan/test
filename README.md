# Linear research title prefix automation

This repository contains a small helper for Linear issue status-change
automations. When an issue status changes to `to research`, the helper returns an
update action that prefixes the issue title with `Cursor researching`.

The handler ignores unrelated triggers, non-research statuses, and titles that
already start with the prefix.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching payload, the command prints:

```json
{"action": "update_issue_title", "issueId": "POI-5052", "title": "Cursor researching: Existing title"}
```

For non-matching payloads, the command exits successfully without output.

## Tests

```bash
python3 -m unittest -v
```
