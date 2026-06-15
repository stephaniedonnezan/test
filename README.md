# Linear research title prefix

This repository contains a small handler for Linear status-change automation
payloads. When an issue changes status to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The CLI prints either the JSON update action or `null`.

## Tests

```bash
python3 -m unittest -v
```
