# Linear issue title research marker

This repository contains a small helper for Cursor automations handling Linear issue status changes.

When an issue status changes to `to research`, `linear_title_prefix.py` builds an `update_issue_title` action that prefixes the issue title with `Cursor researching`. Other statuses are ignored, and already-prefixed titles are left unchanged.
