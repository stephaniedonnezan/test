# Linear issue title prefix

This repository contains a small JSON-in/JSON-out helper for Linear webhook
automations.

When an issue status changes to `to research`, `linear_title_prefix.py` builds
an action to update the issue title with the `Cursor researching` prefix:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-2604",
  "title": "Cursor researching: Manage grey third-party sources of H2"
}
```

The helper is idempotent and returns no action if the title already starts with
`Cursor researching`.

## Usage

Pipe a Linear webhook payload to the script:

```sh
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```sh
python3 -m unittest -v
```
