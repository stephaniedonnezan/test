# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automations.

When an issue status changes to `to research`, `linear_title_prefix.py` returns
an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4278",
  "title": "Cursor researching: follow up downstream emissions"
}
```

The handler ignores non-status-change events, statuses other than `to research`,
and titles that already start with `Cursor researching`.

Run the unit tests with:

```sh
python3 -m unittest -v
```
