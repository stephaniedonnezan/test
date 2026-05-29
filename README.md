# Linear issue title prefix automation

Builds a Linear issue title update action when an issue status changes to
`To Research`.

```bash
python3 linear_title_prefix.py < event.json
```

For matching status-change payloads, the handler emits:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4680",
  "title": "Cursor researching: Missing UBA POS preview in Container Logic Closing tab."
}
```

Non-matching payloads produce no output.
