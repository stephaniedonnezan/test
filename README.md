# Linear research title prefix

This repository contains a small handler for Linear/Cursor automation payloads.
When an issue status changes to `to research`, it produces an idempotent action
to prefix the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5033",
  "title": "Cursor researching: CO2 inputs optional proof file"
}
```

Run the tests with:

```bash
python3 -m unittest -v
```
