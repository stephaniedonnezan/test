# Linear issue title prefix automation

This repository contains a small handler that builds a Linear issue title update
when an issue status changes to `to research`.

For matching status-change events, the handler returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4983",
  "title": "Cursor researching: Existing issue title"
}
```

Events that are not status changes, do not target `to research`, already start
with `Cursor researching`, or do not include an issue id and title are ignored.

Run the tests with:

```sh
python3 -m unittest -v
```
