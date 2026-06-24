# Linear research title prefix

This repository contains a small handler for Linear issue status-change automations.

`build_issue_title_update(event)` returns an `update_issue_title` action when a Linear issue
moves to `To Research`, prefixing the title with:

```text
Cursor researching: <existing title>
```

The handler ignores unrelated status changes, non-status triggers, malformed payloads, and
titles that already start with `Cursor researching`.

Run the tests with:

```bash
python3 -m unittest -v
```
