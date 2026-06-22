# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automations.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an `update_issue_title` action that prefixes the issue title with
`Cursor researching`. Other status changes are ignored, and titles that already
start with `Cursor researching` are left unchanged.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

The script prints the update action as JSON when the payload should change the
issue title; otherwise it exits successfully without output.
