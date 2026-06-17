# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automation payloads.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.
Other status changes and already-prefixed titles are ignored.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The script prints either an `update_issue_title` action or `null`.

## Tests

```bash
python3 -m unittest -v
```
