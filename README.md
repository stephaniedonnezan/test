# Linear issue title automation

Builds a Linear issue title update when a status-change payload moves an issue
to `to research`.

The handler returns an `update_issue_title` action that prefixes the existing
title with `Cursor researching` while avoiding duplicate prefixes.
