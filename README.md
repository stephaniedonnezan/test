# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations.

When a Linear issue status changes to `to research`, `linear_title_prefix.py`
builds an issue title update action that prefixes the title with
`Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4809",
  "title": "Cursor researching: Reduce number of entityManager.save to one."
}
```

The helper accepts flat Cursor trigger contexts as well as nested Linear issue
webhook payloads, normalizes status casing/separators, and avoids duplicating an
existing `Cursor researching` prefix.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

The script prints the update action as JSON, or `null` when the event should not
change the issue title.

## Tests

```bash
python3 -m unittest -v
```
