# Linear research title prefix automation

This repository contains a small, side-effect-free handler for Cursor's Linear
automation trigger. When a Linear issue status-change event moves an issue to
`to research`, `build_issue_title_update` returns an action that prefixes the
issue title with `Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```
