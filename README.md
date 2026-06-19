# Linear issue title prefix

This repository contains a small helper for Linear/Cursor automations.

When a Linear issue status changes to `to research`, `linear_title_prefix.py`
builds an action that prefixes the issue title with:

```text
Cursor researching
```

Example:

```bash
python3 linear_title_prefix.py event.json
```

For a matching status-change payload, the command emits:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3091",
  "title": "Cursor researching: [FE] Dialog refinment"
}
```

For non-matching payloads, it emits `{}`.

Run tests with:

```bash
python3 -m unittest -v
```
