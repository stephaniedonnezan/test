# Linear issue title prefix automation

Adds a `Cursor researching` title prefix when a Linear issue status changes to
`to research`.

The main entrypoint is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an `update_issue_title` action when the
incoming payload is a status-change event whose new status normalizes to
`to research`; otherwise it returns `None`.
