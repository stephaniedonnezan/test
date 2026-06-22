# Linear issue title research prefix

This repository contains a small handler for Cursor/Linear automation payloads. It
returns an issue-title update when a Linear issue status changes to `to research`.

The generated update prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4171",
  "title": "Cursor researching: Reduce transaction lifetime"
}
```

No update is returned for other statuses, non-status triggers, missing issue data,
or titles that already begin with `Cursor researching`.

## Run tests

```sh
python3 -m unittest -v
```

## Smoke test the CLI

```sh
echo '{"trigger":"status_changed","newStatus":"to research","id":"POI-4171","title":"Reduce transaction lifetime"}' \
  | python3 linear_title_prefix.py
```
