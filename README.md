# Linear issue title prefix automation

Builds a title-update action when a Linear issue status changes to `to research`.

```bash
python3 linear_title_prefix.py < payload.json
```

For matching events, the handler prints JSON like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4034",
  "title": "Cursor researching: The grouping by trip errors"
}
```

Non-matching events produce no output.
