# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue status changes to `to research`, the handler builds an action that
prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

The module exposes `build_issue_title_update(event)`, which returns an
`update_issue_title` action dictionary or `None` when no title update is needed.

## Tests

```bash
python3 -m unittest -v
```
