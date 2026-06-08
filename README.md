# Linear issue title prefix automation

This repository contains a small, dependency-free handler for Cursor/Linear
automation payloads.

When an issue status-change event moves to `to research`, the handler returns an
action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4800",
  "title": "Cursor researching: []MB Grid Consumption zeros"
}
```

Run the tests with:

```bash
python3 -m unittest -v
```

The CLI also accepts a JSON payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```
