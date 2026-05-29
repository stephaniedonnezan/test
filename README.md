# Linear issue title automation

This repository contains a small handler for Linear issue status-change
automation payloads.

When an issue status changes to `To Research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.
