# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Cursor/Linear
status-change automations.

When a Linear issue status changes to `to research`, the handler returns an
action asking the caller to prefix the issue title with `Cursor researching`.
Other statuses, non-status-change triggers, and titles that already start with
the prefix are ignored.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

Matching events print an action like:

```json
{"action": "update_issue_title", "issueId": "POI-4961", "title": "Cursor researching: Remove Subscribe button on invite"}
```

Non-matching events exit successfully without printing an action.

## Tests

```bash
python3 -m unittest -v
```
