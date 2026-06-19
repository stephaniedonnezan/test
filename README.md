# Linear issue title automation

Adds `Cursor researching` to a Linear issue title when an issue status changes to
`to research`.

## Usage

Pipe a Cursor/Linear automation payload into the handler:

```bash
python3 linear_title_prefix.py < payload.json
```

When the payload is a status-change event for the `to research` status, the
handler prints an action for the automation platform:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3023",
  "title": "Cursor researching: Metric tonne to be used instead of ton"
}
```

For other events or statuses it prints `null`.
