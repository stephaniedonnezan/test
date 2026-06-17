# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the helper builds an
action that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching status-change event, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4994",
  "title": "Cursor researching: No way to delete a site"
}
```

Non-matching events produce no output. Existing `Cursor researching` prefixes
are preserved without duplication.

## Tests

```bash
python3 -m unittest -v
```
