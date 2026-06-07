# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

## Usage

Pass the automation event JSON on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4831",
  "title": "Cursor researching: [Energy Allocation] GoO Cancelation Deletion"
}
```

For non-matching events, it exits with code `1` and no output.

## Test

```bash
python3 -m unittest -v
```
