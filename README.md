# Linear issue title prefix automation

Adds `Cursor researching` to Linear issue titles when an issue status changes to
`To Research`.

## Usage

Pass a Linear/Cursor trigger payload as JSON on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

When the payload represents a status change into `To Research`, the script emits
an `update_issue_title` action:

```json
{"action": "update_issue_title", "issueId": "POI-4944", "title": "Cursor researching: HubSpot lead routing & sales handoff"}
```

Non-matching payloads emit `null`.
