# Linear research title automation

This repository contains a small handler for Linear issue status-change
automation events.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action to prefix the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4235",
  "title": "Cursor researching: Existing title"
}
```

Events that are not status changes, do not move to `to research`, or already
begin with `Cursor researching` are ignored.

## Test

```sh
python3 -m unittest -v
```
