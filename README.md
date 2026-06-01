# Linear issue title prefix

Small helper for Linear automation payloads. When an issue status-change event
moves an issue to `to research`, the helper returns an `update_issue_title`
action that prefixes the title with `Cursor researching:`.
