# Linear issue title prefix

Builds an `update_issue_title` action for Linear issue status-change events when the
new status is `to research`.

Matching issues receive a `Cursor researching: ` title prefix unless the title is
already prefixed.
