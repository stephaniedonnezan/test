# Linear research title prefix automation

This repository contains a small, side-effect-free helper for Linear issue
automation. When an issue status-change event moves an issue to `to research`,
`linear_title_prefix.py` returns an action to update the issue title with the
`Cursor researching` prefix:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5033",
  "title": "Cursor researching: CO2 inputs optional proof file"
}
```

The helper accepts Cursor automation trigger payloads and common Linear webhook
payload shapes. It ignores non-status updates, non-research statuses, and titles
that already begin with `Cursor researching`.

Run tests with:

```sh
python3 -m unittest -v
```
