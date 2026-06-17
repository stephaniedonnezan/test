# Linear research title prefix

This automation helper builds a Linear issue title update when an issue status
changes to `to research`.

```bash
python3 linear_title_prefix.py < payload.json
```

For matching payloads, the helper prints an action like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4820",
  "title": "Cursor researching: Empty link dialog if no possible allocations"
}
```

Non-matching payloads, missing issue fields, and titles that already start with
`Cursor researching` produce no action.
