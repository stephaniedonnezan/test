# Linear research title prefix

This repository contains a small Linear automation helper. When a Linear issue
status-change payload indicates the issue moved to `to research`, the helper
builds an issue title update action that prefixes the title with
`Cursor researching`.

```bash
python3 linear_title_prefix.py < payload.json
```

The command prints JSON like:

```json
{"action": "update_issue_title", "issueId": "POI-5045", "title": "Cursor researching: Existing title"}
```

Run the tests with:

```bash
python3 -m unittest -v
```
