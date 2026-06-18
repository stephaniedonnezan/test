# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations.

When a Linear issue status changes to `to research`, the handler returns an
action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5071",
  "title": "Cursor researching: User Manual lives in the repo"
}
```

No action is returned for other status changes, non-status updates, missing
issue data, or titles that already begin with `Cursor researching`.

Run tests with:

```sh
python3 -m unittest -v
```
