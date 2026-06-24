# Linear issue title prefix automation

This repository contains a small helper for Linear/Cursor automations.

`linear_title_prefix.py` exposes `build_issue_title_update(event)`, which
returns an `update_issue_title` action when an issue status-change event moves
to `to research`. The generated title is prefixed with:

```text
Cursor researching: <existing title>
```

Events for other statuses, non-status triggers, missing issue data, or titles
that already start with `Cursor researching` return `None`.
