# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves to `to research`, the handler returns an
issue-title update action that prefixes the title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4483",
  "title": "Cursor researching: Gather ETS daily prices"
}
```

The handler accepts the flat `triggerContext` payload used by Cursor
Automations, as well as common nested Linear issue update webhook shapes. It
does not return an action for other statuses, other event types, missing issue
data, or titles that already start with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
