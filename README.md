# Linear issue title prefix automation

This repository contains a small helper for Linear status-change automations.
When an issue is moved to `to research`, the helper builds an action payload to
prefix the issue title with `Cursor researching`.

## Usage

Pass the Linear/Cursor webhook payload as JSON on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

For matching status changes, the script prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5065",
  "title": "Cursor researching: UBA POS should not be modifiable"
}
```

For non-matching events it prints `null`.

## Test

```bash
python3 -m unittest -v
```
