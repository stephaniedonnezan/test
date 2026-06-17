# Linear research title prefix

This repository contains a small helper for Cursor/Linear automation payloads.

`build_issue_title_update(event)` returns an action like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5030",
  "title": "Cursor researching: Ability to fetch data from QA and Prod safely"
}
```

The action is returned only when an issue status-change event moves to `To
Research`. Existing titles that already start with `Cursor researching` are
left unchanged.

Run tests with:

```sh
python3 -m unittest -v
```
