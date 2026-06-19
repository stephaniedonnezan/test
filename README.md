# Linear issue title prefix automation

This repository contains a small helper for Linear status-change automations.

When an issue status changes to `to research`, `linear_title_prefix.py` returns
an action instructing the caller to prefix the issue title with
`Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3626",
  "title": "Cursor researching: Refine the Meters Page dialogs"
}
```

The handler accepts flat Cursor automation payloads and common nested Linear
webhook payloads. It ignores unrelated status changes, non-status triggers,
missing issue details, and titles that already start with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
