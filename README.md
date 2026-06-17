# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when the issue status changes to
`to research`.

The automation logic lives in `linear_title_prefix.py`. It accepts Cursor
automation trigger payloads and Linear webhook-style payloads, then returns an
`update_issue_title` action when the title should be changed.
