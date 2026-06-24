# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change payloads.

When an issue moves to `to research`, `build_issue_title_update(event)` returns
an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5102",
  "title": "Cursor researching: Phase 1: Backend"
}
```

Non-status changes, status changes to other workflow states, and titles that
already start with `Cursor researching` return `null`.

## Development

Run the test suite:

```sh
python3 -m unittest -v
```

Smoke-test a payload from stdin:

```sh
python3 linear_title_prefix.py < payload.json
```
