# Linear research title prefix automation

This repository contains a small handler that builds a Linear issue title update
when an issue changes status to `to research`.

The handler returns an `update_issue_title` action with the title prefixed as:

```text
Cursor researching: <existing title>
```

It ignores non-status changes, non-research statuses, missing issue metadata, and
titles that already start with `Cursor researching`.
