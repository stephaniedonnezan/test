# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation events.

When an issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching:`.

The handler ignores:

- status changes to any other status
- non-status-change events
- issues whose title already starts with `Cursor researching`
- payloads that do not include both an issue id and title

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
