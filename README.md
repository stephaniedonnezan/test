# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status changes to `to research`, the helper builds an issue-title
update that prefixes the title with `Cursor researching`.

## Behavior

- Matches status-change events whose new status normalizes to `to research`.
- Supports flat Cursor `triggerContext` payloads and nested Linear issue update
  webhook payloads.
- Returns an `update_issue_title` action containing the issue id and prefixed
  title.
- Leaves unrelated triggers and statuses unchanged by returning `None`.
- Skips titles that already start with `Cursor researching` to avoid duplicate
  prefixes.

## Usage

```bash
python3 linear_title_prefix.py <<'JSON'
{
  "triggerContext": {
    "trigger": "status_changed",
    "newStatus": "to research",
    "id": "POI-4962",
    "title": "User role not persisiting upon invitation"
  }
}
JSON
```

Output:

```json
{"action": "update_issue_title", "issueId": "POI-4962", "title": "Cursor researching: User role not persisiting upon invitation"}
```

## Tests

```bash
python3 -m unittest -v
```
