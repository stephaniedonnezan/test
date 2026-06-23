# Linear research title prefix

This repository contains a small, side-effect-free helper for Cursor's Linear
automation:

- when a Linear issue status-change event moves to `to research`, return an
  action that prefixes the issue title with `Cursor researching`;
- ignore unrelated events, other statuses, missing issue data, and titles that
  are already prefixed.

The Python entry point is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an `update_issue_title` action dictionary
or `None` when no update should be applied.

Run the tests with:

```bash
python3 -m unittest -v
```
