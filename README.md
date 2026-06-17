# Linear research title prefix

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status-change event moves an issue to `to research`, the helper
returns an action instructing the caller to prefix the issue title with
`Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4966",
  "title": "Cursor researching: Invite landing page"
}
```

The helper is intentionally side-effect free: it does not call Linear directly.
It accepts flat Cursor `triggerContext` payloads and nested Linear issue update
payloads, and it avoids adding the prefix more than once.

## Run tests

```bash
python3 -m unittest -v
```

## CLI usage

```bash
python3 linear_title_prefix.py < event.json
```
