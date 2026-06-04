# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

Run the test suite with:

```sh
python3 -m unittest -v
```

The handler can also read a JSON event from stdin:

```sh
python3 linear_title_prefix.py < event.json
```
