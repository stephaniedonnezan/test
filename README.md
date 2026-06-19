# Linear title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler builds an
issue title update that prefixes the current title with `Cursor researching`.

## Usage

Pass a JSON payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

If the payload represents a matching status change, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5051",
  "title": "Cursor researching: Create error if compliant co2 input is not set as 1"
}
```

Non-matching payloads produce no output. Existing `Cursor researching` prefixes
are left unchanged.

## Tests

```bash
python3 -m unittest -v
```
