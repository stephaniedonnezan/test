# Linear issue title automation

This repository contains a small handler for Linear/Cursor status-change
automations.

`build_issue_title_update(event)` returns an `update_issue_title` action when an
issue status changes to `to research`, adding `Cursor researching` to the issue
title:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4765",
  "title": "Cursor researching: Remove the fallback"
}
```

The handler ignores unrelated status changes, non-status updates, malformed
payloads, and titles that already start with `Cursor researching`.

Run tests with:

```sh
python3 -m unittest -v
```
