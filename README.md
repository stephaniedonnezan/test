# Linear research title prefix

This repository contains a small handler for Linear status-change automation.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4517",
  "title": "Cursor researching: Delete the S3 pos file after the transaction completes"
}
```

The handler ignores non-status changes, non-research statuses, missing issue
metadata, and titles that already start with `Cursor researching`.

## Usage

Run the tests:

```sh
python3 -m unittest -v
```

Run the handler as a CLI by piping a JSON event to stdin:

```sh
echo '{"trigger":"status_changed","newStatus":"To Research","id":"POI-4517","title":"Delete S3 file"}' \
  | python3 linear_title_prefix.py
```
