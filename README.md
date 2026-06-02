# Linear issue title automation

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `to research`, the handler returns an
action that prefixes the issue title with `Cursor researching`.

The handler is intentionally side-effect free: callers can pass the Linear
automation payload to `build_issue_title_update` and apply the returned action
with their Linear client.
