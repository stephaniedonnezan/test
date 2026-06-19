# Linear research title prefix

This repository contains a small helper for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, it builds an issue title
update that prefixes the current title with `Cursor researching`.

The helper returns no action for other statuses, non-status updates, missing issue
metadata, or titles that already begin with the prefix.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching payload, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3869",
  "title": "Cursor researching: Quick win: Turn2X feedback - counter reading bad request"
}
```

For non-matching payloads, it exits successfully without printing anything.

## Tests

```bash
python3 -m unittest -v
```
