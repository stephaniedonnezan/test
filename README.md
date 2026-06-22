# Linear research status title prefix

This repository contains a small handler for Linear issue status-change
automation. When an issue moves to `to research`, the handler returns an action
to prefix the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

The command prints an `update_issue_title` action for matching events and prints
nothing for events that should be ignored.

## Tests

```bash
python3 -m unittest -v
```
