# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `To Research`, the handler returns an action
to update the issue title with the `Cursor researching` prefix:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4818",
  "title": "Cursor researching: Existing issue title"
}
```

The handler ignores unrelated status changes, non-status events, missing issue
metadata, and titles that already start with `Cursor researching`.

## Usage

Run the unit tests:

```sh
python3 -m unittest -v
```

Run the CLI against a JSON trigger payload:

```sh
python3 linear_title_prefix.py < payload.json
```
