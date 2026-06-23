# Linear title prefix automation

This repository contains a small helper for Linear status-change automations.

`linear_title_prefix.py` exposes `build_issue_title_update(event)`, which
returns an issue-title update action when a Linear issue status changes to
`to research`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5058",
  "title": "Cursor researching: Move the mb-data-manager into the psqo module"
}
```

Non-matching events return `None`. The module can also be run as a CLI that
reads a JSON event from stdin and prints the action when one is needed.

Run tests with:

```bash
python3 -m unittest -v
```
