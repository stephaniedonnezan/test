# Linear research title prefix

This repository contains a small handler for the Linear automation that prefixes
an issue title with `Cursor researching` when the issue status changes to
`to research`.

## Behavior

`build_issue_title_update(event)` returns an action dictionary when all of these
conditions are met:

- the payload represents a Linear issue status-change event,
- the new status normalizes to `to research`, and
- the issue title does not already start with `Cursor researching`.

Example return value:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4982",
  "title": "Cursor researching: Deliveries lifecycle (production site)"
}
```

For non-matching events, the function returns `None`.

The handler accepts both flat Cursor trigger context payloads and common nested
Linear webhook payloads.

## Development

Run the unit tests with:

```bash
python3 -m unittest -v
```
