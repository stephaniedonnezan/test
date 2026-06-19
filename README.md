# Linear issue title research prefix

Adds `Cursor researching` to a Linear issue title when an issue status-change
event moves the issue to `to research`.

The automation entry point is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an update action when the event matches the
research status transition, or `None` when no title change is needed.
