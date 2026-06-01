# Linear issue title automation

Adds the `Cursor researching` title prefix when a Linear issue status changes
to `to research`.

The main entrypoint is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an `update_issue_title` action or `None`
when the event should be ignored.
