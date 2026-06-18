# Linear issue title research prefix

This repository contains a small helper for Linear status-change automations.

`linear_title_prefix.py` reads a Linear issue event and returns an
`update_issue_title` action when the issue moves to the `to research` status.
The generated title is prefixed with `Cursor researching:`.
