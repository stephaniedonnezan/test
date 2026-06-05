# Linear research title automation

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves to `to research`, the handler returns an
`update_issue_title` action that prefixes the title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The command prints either a JSON update action or `null`.

## Tests

```bash
python3 -m unittest -v
```
