# Linear title prefix automation

This repository contains a small helper for Cursor/Linear automation payloads.
When a Linear issue status changes to `To Research`, the helper returns an
action that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For matching payloads, the script prints JSON like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4968",
  "title": "Cursor researching: Multi member interruption screen needs Atmen brand and legal notice"
}
```

For non-matching events, invalid payloads, or titles that already start with
`Cursor researching`, the script exits successfully without output.
