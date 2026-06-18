# Linear issue title prefix automation

This repository contains a small helper for Linear status-change automations.
When an issue moves to `To Research`, the helper builds an action that prefixes
the issue title with `Cursor researching`.

## Usage

Pass the webhook or Cursor automation payload on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

For matching issue status changes, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4932",
  "title": "Cursor researching: Existing issue title"
}
```

For all other events, it prints `null`.

## Development

Run the tests with:

```bash
python3 -m unittest -v
```
