# Linear issue title prefix automation

This repository contains a small handler for Linear/Cursor automation payloads.
When a Linear issue status changes to `to research`, it builds an action that
prefixes the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching payload, the script prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4963",
  "title": "Cursor researching: User role & rights cannot be seen by invitee"
}
```

Run the test suite with:

```bash
python3 -m unittest -v
```
