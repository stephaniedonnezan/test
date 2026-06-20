# Linear issue title prefix

This repository contains a small helper for Linear automation payloads.

`build_issue_title_update(event)` returns an update action when an issue status
change moves to `to research`, adding the `Cursor researching` prefix to the
issue title:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4578",
    "title": "Cursor researching: Existing issue title",
}
```

Events that are not status changes, do not move to `to research`, are missing
an issue id/title, or already have the prefix are ignored.
