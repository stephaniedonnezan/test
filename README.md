# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automation payloads.
When an issue status change moves to `To Research`, it emits an action to prefix
the issue title with `Cursor researching`.

```sh
python3 linear_title_prefix.py < payload.json
```

For example, a matching payload returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4772",
  "title": "Cursor researching: In the methane excel export, use 0 instead of N/A"
}
```

Run tests with:

```sh
python3 -m unittest -v
```
