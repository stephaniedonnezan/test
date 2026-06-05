# Linear research title prefix

This repository contains a small, side-effect-free handler for the Cursor
automation that reacts to Linear issue status changes.

When an issue status-change payload moves an issue to `to research`,
`build_issue_title_update` returns an action for the caller to update the issue
title to:

```text
Cursor researching: <existing title>
```

The handler ignores unrelated events, non-research statuses, missing issue
fields, and titles that already start with `Cursor researching`.

Run the tests with:

```bash
python3 -m unittest -v
```
