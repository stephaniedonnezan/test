# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation payloads.

`build_issue_title_update(event)` returns an `update_issue_title` action when an
issue moves into `To Research`, adding the title prefix:

```text
Cursor researching: <issue title>
```

The handler accepts both flat Cursor `triggerContext` payloads and nested Linear
webhook payloads. It ignores non-status triggers, other statuses, missing issue
metadata, and titles that already start with `Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
