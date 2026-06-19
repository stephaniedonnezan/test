# Linear issue title prefix

This repository contains a small helper for Linear/Cursor automations that need
to mark issues as being researched.

When an issue status-change event moves to `to research`,
`build_issue_title_update(event)` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5031",
  "title": "Cursor researching: Improve performance of timeZoneObject()"
}
```

For all other events, missing issue data, or titles already starting with
`Cursor researching`, it returns `None`.

Run the tests with:

```sh
python3 -m unittest -v
```
