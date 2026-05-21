# Linear issue title prefix helper

This repository contains a small helper that builds a Linear issue title update
when an issue status changes to `to research`.

Given a supported Linear status-change payload, the helper returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.
