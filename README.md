# Linear research title prefix

This repository contains a small handler for Linear status-change automations.

When a Linear issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

## Usage

Pipe a JSON event into the script:

```sh
python3 linear_title_prefix.py < event.json
```

Run tests with:

```sh
python3 -m unittest -v
```
