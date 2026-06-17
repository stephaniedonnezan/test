# Linear issue title research status automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status changes to `to research`, the helper returns a title update
action that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching status-change payload, the CLI prints an action such as:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5020",
  "title": "Cursor researching: Issues should always try to link"
}
```

Non-matching payloads print `null`. Existing titles that already start with
`Cursor researching` are left unchanged.
