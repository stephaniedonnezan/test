# Linear research title prefix

This repository contains a small automation helper for Linear issue status
changes. When an issue status changes to `to research`, the helper builds an
action to prefix the issue title with `Cursor researching`.

## Usage

Pass a Cursor automation trigger context or Linear webhook payload as JSON on
stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

If the payload represents an issue moving to `to research`, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4981",
  "title": "Cursor researching: Super admin"
}
```

Non-matching payloads print nothing. Titles that already start with
`Cursor researching` are left unchanged.

## Tests

```bash
python3 -m unittest -v
```
