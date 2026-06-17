# Linear issue title prefix

This repository contains a small Cursor/Linear automation helper. When a Linear
issue status changes to `to research`, the helper returns an update action that
adds `Cursor researching` to the issue title.

Example:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5042",
  "title": "Cursor researching: Offtakers configuration (commercial targets + emissions)"
}
```

The helper is idempotent: if a title already starts with `Cursor researching`,
it returns no update.

## Usage

Pass the Linear/Cursor webhook payload on stdin:

```sh
python3 linear_title_prefix.py < event.json
```

Run tests with:

```sh
python3 -m unittest -v
```
