# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `To Research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

The handler accepts Cursor Automation trigger payloads, including the cloud
`automation_trigger_info.triggerContext` wrapper, as well as common nested
Linear issue webhook payloads.
