# Linear title prefix automation

This repository contains a small helper for Cursor/Linear automation payloads.
When a Linear issue status changes to `To Research`, the helper returns an
issue title update that prepends `Cursor researching: `.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For matching events, the CLI prints a JSON action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4999",
  "title": "Cursor researching: If no loading event"
}
```

Events that are not status changes to `To Research`, or titles that already
start with `Cursor researching`, produce no output.

## Tests

```bash
python3 -m unittest -v
```
