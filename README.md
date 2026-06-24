# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automations.

`linear_title_prefix.build_issue_title_update(event)` returns an
`update_issue_title` action when an issue status changes to `To Research`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3477",
  "title": "Cursor researching: Change name from Filling to Loading event"
}
```

The handler accepts flat automation trigger payloads as well as nested Linear
webhook payloads, normalizes status casing/separators, and does not add the
`Cursor researching` prefix when the title already starts with it.

To use it as a CLI, pass a JSON event on stdin:

```sh
python3 linear_title_prefix.py < event.json
```
