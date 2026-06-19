# Linear issue title prefix automation

Builds an issue-title update action when a Linear issue status changes to
`to research`.

When the event matches, `linear_title_prefix.py` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4307",
  "title": "Cursor researching: Spreadsheet app agnostic for testing"
}
```

The handler supports Cursor Cloud `automation_trigger_info.triggerContext`
payloads and nested Linear issue-update payloads. It skips events that are not
status changes to `to research` and avoids adding the `Cursor researching`
prefix more than once.

Run the unit tests with:

```bash
python3 -m unittest -v
```
