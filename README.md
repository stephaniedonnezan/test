# Linear issue title prefix automation

This repository contains a small handler for Cursor automations triggered by
Linear issue status changes.

When an issue moves to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-123",
  "title": "Cursor researching: Existing issue title"
}
```

The handler ignores unrelated events, non-research statuses, missing issue
details, and titles that already start with the prefix.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
