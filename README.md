# Linear issue title prefix

This repository contains a small helper for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the helper builds a title
update action that prefixes the issue title with `Cursor researching:`.

## Usage

Pass the webhook event JSON on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

For a matching status change, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4703",
  "title": "Cursor researching: Existing issue title"
}
```

If the event is not a status change to `to research`, or the title already has
the marker, the command prints `null`.

## Tests

```bash
python3 -m unittest -v
```
