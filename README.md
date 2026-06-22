# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status changes to `to research`, the helper returns the title
update that adds the `Cursor researching` prefix.

## Usage

Pipe a Linear/Cursor webhook payload into the CLI:

```bash
python3 linear_title_prefix.py < payload.json
```

For a qualifying status change, the script prints an action object:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4322",
  "title": "Cursor researching: Refine the storage loss dialog"
}
```

For non-qualifying payloads, it prints `null`.
