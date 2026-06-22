# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `To Research`, the handler returns an action
that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The script prints an `update_issue_title` action when the event should be
handled, or `null` when no title update is required.

## Tests

```bash
python3 -m unittest -v
```
