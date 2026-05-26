# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status-change event moves an issue to `to research`, the
handler returns an action that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

The command prints an `update_issue_title` action when the event should update
the issue title, and prints nothing for events that should be ignored.

## Tests

```bash
python3 -m unittest -v
```
