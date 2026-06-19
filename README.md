# Linear title prefix automation

This repository contains a small Linear webhook helper that adds
`Cursor researching` to an issue title when the issue status changes to
`to research`.

## Usage

Pass a Linear/Cursor webhook payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

When the payload represents a status change to `to research`, the script emits
an action object:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4988",
  "title": "Cursor researching: Existing title"
}
```

For non-matching events, missing issue data, or titles that already start with
`Cursor researching`, the script exits without output.

## Tests

```sh
python3 -m unittest -v
```
