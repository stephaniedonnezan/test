# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automations. When an issue status changes to `To Research`, the handler returns
an action to prefix the issue title with `Cursor researching`.

## Usage

Pipe a Linear webhook or automation payload into the module:

```sh
python3 linear_title_prefix.py < payload.json
```

For matching events, it prints an `update_issue_title` action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4895",
  "title": "Cursor researching: improve cascade rules for the psqo entity"
}
```

Non-matching events produce no output.

## Tests

```sh
python3 -m unittest -v
```
