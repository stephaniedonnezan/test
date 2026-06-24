# Linear research title prefix automation

This repository contains a small, side-effect-free helper for Linear issue
status-change automations.

`build_issue_title_update(event)` returns an update action when an issue status
changes to `to research`:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-5132",
    "title": "Cursor researching: Write e2e tests",
}
```

Events that do not represent a status change to `to research`, are missing an
issue id or title, or already start with `Cursor researching` are ignored.

The module can also be used as a CLI that reads a JSON event from stdin and
prints the update action when one is needed:

```bash
python3 linear_title_prefix.py < event.json
```
