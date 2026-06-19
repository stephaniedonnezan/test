# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automations.

When an issue status changes to `to research`, `build_issue_title_update(event)`
returns an action that updates the issue title to start with:

```text
Cursor researching: <current title>
```

The handler ignores other status changes, non-status-change events, and titles
that already start with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

The CLI prints the JSON update action when the event should update the title.
