# Linear issue title automation

Adds `Cursor researching` to a Linear issue title when the issue status changes
to `to research`.

The handler accepts flat Cursor automation payloads and nested Linear webhook
payloads. It returns an action object that an automation runner can use to
update the issue title:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5082",
  "title": "Cursor researching: Bug: stoichemistry"
}
```

Run the unit tests with:

```bash
python3 -m unittest -v
```
