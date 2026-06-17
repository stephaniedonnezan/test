# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `To Research`, the handler prepares an
issue title update that prefixes the current title with `Cursor researching`.

## Behavior

- Matches status-change triggers such as `status_changed` and `statusChanged`.
- Matches generic Linear update events only when the changed fields include
  `status`, `state`, or `workflowState`.
- Normalizes status values such as `To Research`, `to_research`, and
  `toResearch`.
- Skips titles that already start with `Cursor researching`.
- Supports flat Cursor `triggerContext` payloads and nested Linear `data.issue`
  payloads.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

When the event should update an issue title, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3860",
  "title": "Cursor researching: Meter table should display sites"
}
```

If the event does not match the status transition, the command exits
successfully without printing an action.

## Tests

```bash
python3 -m unittest -v
```
