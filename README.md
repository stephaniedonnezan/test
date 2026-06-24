# Linear issue title prefix automation

This repository contains a small side-effect-free handler for Linear issue
status-change automation.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4896",
    "title": "Cursor researching: Original issue title",
}
```

The handler accepts flat Cursor `triggerContext` payloads and nested Linear
webhook-style payloads. It ignores non-status changes, statuses other than
`to research`, and titles that already start with `Cursor researching`.

## Run tests

```bash
python3 -m unittest -v
```

## CLI smoke check

```bash
echo '{"triggerContext":{"trigger":"status_changed","newStatus":"To Research","id":"POI-4896","title":"Example"}}' \
  | python3 linear_title_prefix.py
```
