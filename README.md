# Linear issue title prefix automation

This repository contains a small, side-effect-free helper for Cursor/Linear
automation payloads.

When a Linear issue status-change event moves an issue to `to research`,
`build_issue_title_update(event)` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4579",
  "title": "Cursor researching: Existing issue title"
}
```

For all other events it returns `null`/`None`.

The helper accepts flat Cursor trigger-context payloads and nested Linear issue
webhook payloads. It avoids adding the `Cursor researching` prefix when the
title already starts with it.

Run tests:

```sh
python3 -m unittest -v
```

CLI smoke check:

```sh
printf '%s\n' '{"trigger":"status_changed","newStatus":"to research","id":"POI-4579","title":"MB export corrections"}' \
  | python3 linear_title_prefix.py
```
