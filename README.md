# Linear issue title prefix automation

This repository contains a small handler for Linear/Cursor automation payloads.
When an issue status changes to `to research`, it builds an action to prefix the
issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The script prints an `update_issue_title` action when the incoming event is a
status-change event moving to `to research`; otherwise it prints nothing.

## Test

```bash
python3 -m unittest -v
```
