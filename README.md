# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear issue status-change
automations.

When an issue status changes to `to research`, `build_issue_title_update`
returns an `update_issue_title` action that prefixes the title with
`Cursor researching`. Other status changes and non-status events are ignored.
