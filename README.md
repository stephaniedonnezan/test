# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear status-change
automation payloads.

When an issue status changes to `to research`, `linear_title_prefix.py` returns
an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5047",
  "title": "Cursor researching: What is a valid default downstream emissions name?"
}
```

The handler ignores other status changes and leaves titles that already start
with `Cursor researching` unchanged.
