# Linear research title prefix

This repository contains a small helper for Cursor/Linear automation events.

`linear_title_prefix.py` inspects a Linear issue status-change payload and
returns an `update_issue_title` action when the issue moves to `To Research`.
The new title is prefixed with `Cursor researching` and existing prefixes are
left unchanged.

Run the tests with:

```bash
python3 -m unittest -v
```
