# Linear issue title prefix helper

This repository contains a small helper for Linear automation events. When an
issue status changes to `to research`, `linear_title_prefix.py` builds an action
to update the issue title with the `Cursor researching` prefix.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4884",
  "title": "Cursor researching: lock qualified outputs"
}
```

The helper supports flat Cursor automation payloads and nested Linear webhook
payloads. It ignores non-status-change events, skips statuses other than
`to research`, and does not add the prefix when the title already starts with
`Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
