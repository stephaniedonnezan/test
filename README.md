# Linear issue research title prefix

This repository contains a small Linear automation helper. When a status-change
event moves an issue into `to research`, the helper builds an action that
prefixes the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

The command prints either an `update_issue_title` action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4902",
  "title": "Cursor researching: Assert timeline consistency before delivery issuance"
}
```

or `null` when no title update should be issued. Existing titles that already
begin with `Cursor researching` are left unchanged.
