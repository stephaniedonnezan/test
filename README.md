# test

## Linear research title prefix

`linear_title_prefix.py` exposes `build_issue_title_update(event)`, which returns an
`update_issue_title` action when a Linear issue status-change payload moves an issue
to `to research`.

Matching issues receive the title prefix `Cursor researching: ` unless the title is
already prefixed. The helper accepts the flat Cursor automation trigger context and
common nested Linear webhook payloads.
