# Linear issue title research marker

This repository contains a small helper for Linear status-change automations.

When an issue status changes to `to research`, `linear_title_prefix.py` builds an
`update_issue_title` action that prefixes the title with `Cursor researching`.
Events for other statuses or titles that already start with the marker are
ignored.

```bash
python3 linear_title_prefix.py < event.json
```

Run tests with:

```bash
python3 -m unittest -v
```
