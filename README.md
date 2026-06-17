# Linear issue title prefix automation

This repository contains a small, dependency-free helper for Cursor automation
payloads from Linear.

When an issue status changes to `to research`, `linear_title_prefix.py` returns
an idempotent action to prefix the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5038",
  "title": "Cursor researching: Original issue title"
}
```

Payloads that do not represent a status change into `to research`, are missing
an issue ID or title, or already start with `Cursor researching` return `null`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
