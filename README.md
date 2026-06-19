# Linear issue title prefix automation

This repository contains a small side-effect-free handler for Linear automation
payloads.

When an issue status-change event moves to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`. Events for other statuses, unrelated issue updates, or
titles that already start with the prefix are ignored.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The script prints a JSON action when the title should be updated, and prints
nothing when no update is needed.

## Tests

```bash
python3 -m unittest -v
```
