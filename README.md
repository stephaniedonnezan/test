# Linear research title prefix helper

This repository contains a small JSON-in/JSON-out helper for Cursor/Linear
automations.

When a Linear issue status-change event moves an issue to `to research`, the
helper returns an action instructing the caller to prefix the issue title with
`Cursor researching`.

```bash
echo '{"trigger":"status_changed","newStatus":"to research","id":"POI-4167","title":"Add type Mixed"}' \
  | python3 linear_title_prefix.py
```

Output:

```json
{"action": "update_issue_title", "issueId": "POI-4167", "title": "Cursor researching: Add type Mixed"}
```

No output is produced for non-status-change events, non-research statuses,
missing issue data, or titles that already start with `Cursor researching`.

## Tests

```bash
python3 -m unittest -v
```
