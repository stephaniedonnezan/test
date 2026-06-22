# Linear research title prefix

This repository contains a small helper for Linear issue status-change
automations.

When an issue status changes to `to research`, `linear_title_prefix.py` builds a
structured action that adds `Cursor researching` to the issue title:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4932",
  "title": "Cursor researching: Improve the Stored File Transaction Delegate implementation"
}
```

The helper is side-effect free. Automation code can call
`build_issue_title_update(event)` and apply the returned action to Linear when it
is not `None`.

It also supports stdin/stdout usage:

```bash
python3 linear_title_prefix.py < webhook-payload.json
```
