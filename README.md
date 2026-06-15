# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automation events.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4895",
    "title": "Cursor researching: improve cascade rules for the psqo entity",
}
```

The handler accepts flat Cursor automation payloads under `triggerContext` and
nested Linear webhook payloads under `data.issue`. It ignores non-status changes,
statuses other than `to research`, and titles that already start with the prefix.

Run the tests with:

```bash
python3 -m unittest -v
```
