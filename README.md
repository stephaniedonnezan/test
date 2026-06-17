# Linear issue title prefix handler

This repository contains a small handler for Linear issue status-change
automation events.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action to prefix the issue title with `Cursor researching`.
Non-matching status changes, non-status issue updates, and already-prefixed
titles are ignored.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Test

```bash
python3 -m unittest -v
```
