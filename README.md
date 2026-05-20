# Linear issue title prefix automation

Builds an `update_issue_title` action for Linear issue status-change events when
the new status is `to research`.

The generated title is prefixed with:

```text
Cursor researching: <original title>
```

The handler is intentionally dependency-free and accepts both the flat Cursor
automation trigger payload shape and nested Linear webhook payloads.
