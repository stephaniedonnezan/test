# Linear research title prefix automation

This repository contains a small Linear automation helper for issue title
updates.

`linear_title_prefix.build_issue_title_update(event)` returns an
`update_issue_title` action when a Linear issue status-change event moves to
`to research`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4758",
  "title": "Cursor researching: Add database checks on transport-segment entity"
}
```

The helper accepts the compact automation `triggerContext` payload as well as
common nested Linear issue webhook payloads. Status matching is
case/separator-insensitive, and titles that already start with
`Cursor researching` are left unchanged.

To run it as a CLI, pass an event payload on stdin or with `--input`:

```sh
python3 linear_title_prefix.py --input event.json
```
