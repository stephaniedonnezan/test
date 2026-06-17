# Linear research status title prefix

This repository contains a small automation helper for Linear issue webhooks.

When an issue status-change event moves an issue to `to research`,
`build_issue_title_update` returns an idempotent title update action that adds
the `Cursor researching` prefix:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4957",
  "title": "Cursor researching: Build anonymised ISCC PoS test-fixture corpus"
}
```

The helper accepts flat Cursor `triggerContext` payloads and common nested
Linear issue webhook payloads. It returns `null` for unrelated triggers,
non-research statuses, missing issue metadata, or titles that already begin
with the prefix.

## Development

Run the test suite with:

```sh
python3 -m unittest -v
```
