# Linear issue title prefix automation

This repository contains a small Linear automation helper for status-change
events. When an issue moves to `To Research`, the helper returns an action that
prefixes the issue title with `Cursor researching`.

## Usage

Pass a Linear automation or webhook payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

When the payload represents a status change to `To Research`, the script prints
JSON describing the title update:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5017",
  "title": "Cursor researching: There seems to be a minimum value when allocating to a prod site"
}
```

For all other events, it exits successfully without output.

## Development

Run the test suite with:

```bash
python3 -m unittest -v
```
