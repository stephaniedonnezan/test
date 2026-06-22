# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue changes status to `to research`, the helper returns an action to
prefix the issue title with `Cursor researching`.

## Usage

Pass a Linear/Cursor webhook payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

If the payload represents an issue status change to `to research`, the command
prints JSON like:

```json
{"action": "update_issue_title", "issueId": "POI-5033", "title": "Cursor researching: CO2 inputs optional proof file"}
```

For unrelated events, already-prefixed titles, or incomplete payloads, it prints
nothing.
