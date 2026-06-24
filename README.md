# Linear issue title research prefix

This repository contains a small handler for Linear status-change automation
payloads. When an issue moves to `to research`, the handler returns an action to
prefix the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching payload, the command prints JSON like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4321",
  "title": "Cursor researching: Existing issue title"
}
```

Payloads that do not represent a status change to `to research`, already have
the prefix, or lack an issue id/title produce no output.

## Tests

```bash
python3 -m unittest -v
```
