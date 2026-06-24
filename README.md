# Linear research title prefix

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action that updates
the issue title to include the `Cursor researching` prefix.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For a matching event, the CLI prints an action payload:

```json
{"action": "update_issue_title", "issueId": "POI-5106", "title": "Cursor researching: Phase 5: Documentation"}
```

For non-matching events, duplicate prefixes, or malformed payloads, it exits
successfully without printing anything.

## Supported payloads

The handler accepts Cursor automation trigger context payloads:

```json
{
  "triggerContext": {
    "trigger": "status_changed",
    "newStatus": "to research",
    "id": "POI-5106",
    "title": "Phase 5: Documentation"
  }
}
```

It also accepts nested Linear webhook-style issue updates where status, state, or
workflow state fields changed.

## Development

Run the test suite with:

```bash
python3 -m unittest -v
```
