# Linear research title prefix

This repository contains a small helper for Cursor automations that react to
Linear issue status changes.

When an issue status changes to `to research`, `build_issue_title_update`
returns an update action that prefixes the issue title with
`Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4679",
  "title": "Cursor researching: Edit Input button missing container logic mass balance"
}
```

Run the tests with:

```sh
python3 -m unittest -v
```
