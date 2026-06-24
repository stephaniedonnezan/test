# Linear issue title prefix automation

This repository contains a small, dependency-free handler for Cursor/Linear
automation payloads.

`build_issue_title_update(event)` returns an update action when a Linear issue
status changes to `to research`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5109",
  "title": "Cursor researching: Existing issue title"
}
```

The handler accepts flat Cursor `triggerContext` payloads and nested Linear issue
webhook payloads, normalizes status/trigger casing and separators, and avoids
adding a duplicate `Cursor researching` prefix.

Run tests with:

```sh
python3 -m unittest -v
```
