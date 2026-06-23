# Linear issue title research prefix

This repository contains a small automation helper for Linear status-change
events.

When an issue status changes to `to research`, `build_issue_title_update(event)`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5100",
  "title": "Cursor researching: Demo POS Extraction for Trader Input"
}
```

The helper accepts Cursor automation trigger payloads under `triggerContext` as
well as nested Linear webhook-style payloads. It ignores unrelated triggers,
non-research statuses, missing issue metadata, and titles that already begin
with `Cursor researching`.

Run the tests with:

```bash
python3 -m unittest -v
```
