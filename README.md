# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when a status-change event
moves the issue to `to research`.

## Usage

Pipe a Cursor automation or Linear webhook payload to the handler:

```bash
python3 linear_title_prefix.py < payload.json
```

When the event matches, the handler prints an action for the caller to apply:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4772",
  "title": "Cursor researching: In the methane excel export, use 0 instead of N/A"
}
```

The handler returns `null` for non-status-change events, statuses other than
`to research`, or titles that already start with `Cursor researching`.
