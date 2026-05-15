# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.

`build_issue_title_update(event)` returns an action when a Linear issue status
change moves the issue to `To Research`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4676",
  "title": "Cursor researching: Improve e2e test"
}
```

No action is returned for other statuses, non-status events, missing issue
metadata, or titles that already begin with `Cursor researching`.

Run the test suite with:

```sh
python3 -m unittest -v
```
