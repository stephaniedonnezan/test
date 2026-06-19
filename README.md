# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear status-change events.
When an issue moves to `to research`, the handler builds an action that prefixes
the Linear issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

The CLI prints an `update_issue_title` action for matching events and prints
nothing for events that should be ignored.
