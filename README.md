# Linear research title prefix

This repository contains a small helper for Cursor/Linear automations that
marks an issue title when the issue status changes to `to research`.

`build_issue_title_update(event)` accepts a Cursor automation payload or a
Linear-style webhook payload and returns an action for the caller to apply:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4811",
  "title": "Cursor researching: Create production site form"
}
```

The helper only returns an action when all of the following are true:

- the event is a status-change event,
- the new status normalizes to `to research`,
- the payload contains an issue id and title,
- the title does not already start with `Cursor researching`.

## CLI usage

The module can also read a JSON event from stdin:

```bash
python3 linear_title_prefix.py < event.json
```

It prints the update action as JSON, or `null` when no title update is needed.

## Tests

```bash
python3 -m unittest -v
```
