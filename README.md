# Linear research title prefix

This repository contains a small handler for Linear status-change automation.

When an issue status changes to `to research`, `build_issue_title_update` returns
an action that prefixes the title with `Cursor researching`:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4619",
    "title": "Cursor researching: Adjust global UI button",
}
```

The handler ignores non-status events, non-research statuses, invalid payloads,
and titles that already start with `Cursor researching`.
