# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations.

When an issue status changes to `to research`, `build_issue_title_update(event)`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-2988",
  "title": "Cursor researching: Put database in a private subnet"
}
```

Non-status-change events, other statuses, missing issue details, and titles that
already start with `Cursor researching` are ignored.

Run tests with:

```sh
python3 -m unittest -v
```
